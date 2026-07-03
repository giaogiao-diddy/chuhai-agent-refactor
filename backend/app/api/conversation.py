import json
import uuid as _uuid
import inspect
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
    ConversationStartRequest,
    ConversationStartResponse,
    ConversationStreamRequest,
)
from app.api.auth_deps import get_current_user_optional
from app.models import User
from app.services.assessment_repository import save_completed_assessment
from app.services.model_provider_repository import get_default_provider, get_provider
from app.services.user_repository import get_or_create_anonymous_user
from config import get_settings

router = APIRouter(prefix="/conversation", tags=["conversation"])


def _has_user_message(state: AgentState) -> bool:
    return any(m.role == "user" for m in state.messages)


def _safe_500_detail() -> str:
    return "AI 暂时不可用，请稍后重试"


def _runner_kwargs(fn, kwargs: dict) -> dict:
    sig = inspect.signature(fn)
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return kwargs
    return {k: v for k, v in kwargs.items() if k in sig.parameters}


async def _resolve_provider_runtime(
    db: AsyncSession,
    provider_id: str | None,
    model_name: str | None,
) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    """Resolve provider from DB → (base_url, api_key, model, provider_id, model_name).
    Returns (None, None, None, None, None) when no DB provider is configured
    (falls back to env var config).
    Raises HTTPException only when a specific provider_id is requested but unavailable.
    """
    if provider_id:
        try:
            pid = _uuid.UUID(provider_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的 provider_id")
        provider = await get_provider(db, pid)
        if provider is None or not provider.enabled:
            raise HTTPException(status_code=400, detail="所选模型不可用")
        model = model_name or provider.default_model
        return provider.base_url, provider.api_key, model, str(provider.id), model

    try:
        provider = await get_default_provider(db)
    except Exception:
        return None, None, None, None, None
    if provider is not None:
        model = model_name or provider.default_model
        return provider.base_url, provider.api_key, model, str(provider.id), model

    # No DB provider configured → env var fallback
    return None, None, None, None, None


@router.post("/start", response_model=ConversationStartResponse)
async def start_conversation(
    request: ConversationStartRequest = ConversationStartRequest(),
    db: AsyncSession = Depends(get_db),
):
    base_url, api_key, model, pid, mname = await _resolve_provider_runtime(
        db, request.provider_id, request.model_name,
    )
    state = append_assistant_message(AgentState(), OPENING_MESSAGE)
    state = state.model_copy(update={"provider_id": pid, "model_name": mname})
    client_state = ConversationClientState.from_agent_state(state)
    return ConversationStartResponse(
        state=client_state,
        assistant_message=OPENING_MESSAGE,
        provider_id=pid,
        model_name=mname,
    )


@router.post("/continue", response_model=ConversationContinueResponse)
async def continue_conversation(
    request: ConversationContinueRequest,
    db: AsyncSession = Depends(get_db),
):
    state = request.state.to_agent_state()
    event = AgentEvent(type="user_message", message=request.message)

    runner_kwargs: dict = {"db_session": db}
    if state.provider_id:
        base_url, api_key, model, _, _ = await _resolve_provider_runtime(
            db, state.provider_id, state.model_name,
        )
        if base_url:
            runner_kwargs.update({"provider_base_url": base_url, "provider_api_key": api_key, "provider_model": model})

    result = await run_agent_event(state, event, **_runner_kwargs(run_agent_event, runner_kwargs))

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
async def continue_conversation_stream(
    request: ConversationStreamRequest,
    db: AsyncSession = Depends(get_db),
):
    state = request.state.to_agent_state()

    stream_kwargs: dict = {"db_session": db}
    if state.provider_id:
        base_url, api_key, model, _, _ = await _resolve_provider_runtime(
            db, state.provider_id, state.model_name,
        )
        if base_url:
            stream_kwargs.update({"provider_base_url": base_url, "provider_api_key": api_key, "provider_model": model})

    async def generate() -> AsyncGenerator[str, None]:
        async for event in run_agent_event_stream(
            state,
            AgentEvent(type="user_message", message=request.message),
            **_runner_kwargs(run_agent_event_stream, stream_kwargs),
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

    finish_kwargs: dict = {"db_session": db}
    if state.provider_id:
        base_url, api_key, model, _, _ = await _resolve_provider_runtime(
            db, state.provider_id, state.model_name,
        )
        if base_url:
            finish_kwargs.update({"provider_base_url": base_url, "provider_api_key": api_key, "provider_model": model})

    result = await run_agent_event(
        state,
        AgentEvent(type="finish_requested"),
        **_runner_kwargs(run_agent_event, finish_kwargs),
    )
    state = result.state

    if result.terminal == TerminalState.MISSING_INFO:
        detail: dict = {"message": "信息不足，请继续补充企业情况"}
        if result.response:
            detail["missing_items"] = result.response.get("missing_items", [])
            detail["next_questions"] = result.response.get("next_questions", [])
        raise HTTPException(status_code=400, detail=detail)
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
