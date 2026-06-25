import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import run_dialogue_graph, run_report_pipeline, run_scoring_pipeline
from app.agent.prompts import SYSTEM_DIALOGUE
from app.agent.state_machine import (
    append_assistant_message,
    append_user_message,
    register_ai_failure,
    should_stop_conversation,
    trim_message_history,
)
from app.db.session import get_db
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
from app.schemas.llm import LLMMessage
from app.services.assessment_repository import save_completed_assessment
from app.services.deepseek_client import DeepSeekClient

router = APIRouter(prefix="/conversation", tags=["conversation"])


def _has_user_message(state: AgentState) -> bool:
    return any(m.role == "user" for m in state.messages)


@router.post("/start", response_model=ConversationStartResponse)
async def start_conversation():
    state = AgentState()
    state = await run_dialogue_graph(state)
    assistant_message = state.messages[-1].content if state.messages else ""
    client_state = ConversationClientState.from_agent_state(state)
    return ConversationStartResponse(state=client_state, assistant_message=assistant_message)


@router.post("/continue", response_model=ConversationContinueResponse)
async def continue_conversation(request: ConversationContinueRequest):
    state = request.state.to_agent_state()
    state = append_user_message(state, request.message)
    state = await run_dialogue_graph(state)
    last_assistant = None
    for msg in reversed(state.messages):
        if msg.role == "assistant":
            last_assistant = msg.content
            break
    client_state = ConversationClientState.from_agent_state(state)
    return ConversationContinueResponse(
        state=client_state,
        assistant_message=last_assistant,
        conversation_round=state.conversation_round,
        should_stop=should_stop_conversation(state),
    )


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/continue-stream")
async def continue_conversation_stream(request: ConversationStreamRequest):
    state = request.state.to_agent_state()
    state = append_user_message(state, request.message)

    async def generate() -> AsyncGenerator[str, None]:
        nonlocal state
        try:
            client = DeepSeekClient()
            llm_messages = [LLMMessage(role="system", content=SYSTEM_DIALOGUE)]
            for msg in state.messages[-12:]:
                llm_messages.append(LLMMessage(role=msg.role, content=msg.content))

            assistant_text = ""
            async for chunk in client.stream_chat(llm_messages, max_tokens=256, temperature=0.2):
                assistant_text += chunk
                yield _sse_event({"type": "delta", "content": chunk})

            if not assistant_text.strip():
                raise ValueError("模型未返回最终 content")
            state = append_assistant_message(state, assistant_text)
            state = trim_message_history(state, max_messages=12)
            client_state = ConversationClientState.from_agent_state(state)
            yield _sse_event({"type": "done", "state": client_state.model_dump()})
        except Exception as e:
            state = register_ai_failure(state, f"continue_stream: {e}")
            client_state = ConversationClientState.from_agent_state(state)
            yield _sse_event({"type": "error", "message": "AI 暂时不可用，请稍后重试", "state": client_state.model_dump()})

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/finish", response_model=ConversationFinishResponse)
async def finish_conversation(
    request: ConversationFinishRequest,
    db: AsyncSession = Depends(get_db),
):
    state = request.state.to_agent_state()

    if state.conversation_round < 1 or not _has_user_message(state):
        raise HTTPException(status_code=400, detail="对话信息不足，无法生成报告")

    state = await run_scoring_pipeline(state)
    state = await run_report_pipeline(state)

    if state.user_report is None or state.lead_report is None:
        raise HTTPException(status_code=500, detail="报告生成失败")

    assessment = await save_completed_assessment(db, state)
    client_state = ConversationClientState.from_agent_state(state)

    return ConversationFinishResponse(
        assessment_id=str(assessment.id),
        state=client_state,
        user_report=state.user_report,
        used_template_report=state.used_template_report,
    )
