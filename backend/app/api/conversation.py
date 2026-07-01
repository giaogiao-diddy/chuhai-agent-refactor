import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.prompts import OPENING_MESSAGE
from app.agent.runner import run_agent_event, run_agent_event_stream
from app.agent.state_machine import append_assistant_message
from app.db.session import get_db
from app.schemas.agent_protocol import AgentEvent, TerminalState
from app.schemas.agent_state import AgentState
from app.schemas.conversation import (
    ConversationClientState,
    ConversationContinueRequest,
    ConversationContinueResponse,
    ConversationFinishRequest,
    ConversationFinishResponse,
    ConversationStartResponse,
    ConversationStreamRequest,
)
from app.api.auth_deps import get_current_user_optional
from app.models import User
from app.services.assessment_repository import save_completed_assessment
from app.services.user_repository import get_or_create_anonymous_user
from config import get_settings

router = APIRouter(prefix="/conversation", tags=["conversation"])


def _has_user_message(state: AgentState) -> bool:
    return any(m.role == "user" for m in state.messages)


def _safe_500_detail() -> str:
    return "AI 暂时不可用，请稍后重试"


@router.post("/start", response_model=ConversationStartResponse)
async def start_conversation():
    state = append_assistant_message(AgentState(), OPENING_MESSAGE)
    client_state = ConversationClientState.from_agent_state(state)
    return ConversationStartResponse(state=client_state, assistant_message=OPENING_MESSAGE)


@router.post("/continue", response_model=ConversationContinueResponse)
async def continue_conversation(request: ConversationContinueRequest):
    state = request.state.to_agent_state()
    event = AgentEvent(type="user_message", message=request.message)
    result = await run_agent_event(state, event)

    if result.terminal == TerminalState.FAILED:
        raise HTTPException(status_code=500, detail=_safe_500_detail())

    assistant_message = result.response.get("assistant_message", "") if result.response else ""
    if not assistant_message:
        raise HTTPException(status_code=500, detail=_safe_500_detail())

    client_state = ConversationClientState.from_agent_state(result.state)
    return ConversationContinueResponse(
        state=client_state,
        assistant_message=assistant_message,
        conversation_round=result.state.conversation_round,
        should_stop=False,
    )


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/continue-stream")
async def continue_conversation_stream(request: ConversationStreamRequest):
    state = request.state.to_agent_state()

    async def generate() -> AsyncGenerator[str, None]:
        async for event in run_agent_event_stream(
            state,
            AgentEvent(type="user_message", message=request.message),
        ):
            yield _sse_event(event)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/finish", response_model=ConversationFinishResponse)
async def finish_conversation(
    request: ConversationFinishRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    state = request.state.to_agent_state()

    if state.conversation_round < 1 or not _has_user_message(state):
        raise HTTPException(status_code=400, detail="对话信息不足，无法生成报告")

    if current_user is not None:
        user_id = current_user.id
    elif request.anonymous_user_id:
        user = await get_or_create_anonymous_user(db, request.anonymous_user_id)
        user_id = user.id
    else:
        raise HTTPException(status_code=401, detail="请先登录")

    result = await run_agent_event(
        state,
        AgentEvent(type="finish_requested"),
    )
    state = result.state

    if result.terminal == TerminalState.MISSING_INFO:
        raise HTTPException(status_code=400, detail="信息不足，请继续补充企业情况")
    if result.terminal == TerminalState.UNSUPPORTED_BRANCH:
        raise HTTPException(status_code=400, detail="深度诊断优先支持已有出海经验企业")
    if result.terminal == TerminalState.FAILED:
        raise HTTPException(status_code=500, detail="报告生成失败，请稍后重试")

    if state.user_report is None or state.lead_report is None:
        raise HTTPException(status_code=500, detail="报告生成失败")

    assessment = await save_completed_assessment(db, state, user_id=user_id)
    client_state = ConversationClientState.from_agent_state(state)

    from app.schemas.report_history import PublicReportSummary
    ur = state.user_report
    settings = get_settings()
    return ConversationFinishResponse(
        assessment_id=str(assessment.id),
        state=client_state,
        report_summary=PublicReportSummary(
            feasibility_score=ur.feasibility_score,
            display_score=ur.display_score,
            tag=ur.tag,
            tag_explanation=ur.tag_explanation,
            preliminary_judgment=ur.preliminary_judgment,
            strengths=ur.strengths,
            risks=ur.risks,
            unlock_hint=ur.unlock_hint,
        ),
        used_template_report=state.used_template_report,
        wechat_qr_url=settings.WECHAT_QR_URL or None,
    )
