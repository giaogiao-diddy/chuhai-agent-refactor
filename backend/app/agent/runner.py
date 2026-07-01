from collections.abc import AsyncGenerator

from app.agent.nodes import apply_extraction_result
from app.agent.state_machine import append_assistant_message, append_user_message
from app.agent.tools.executor import ToolExecutor
from app.agent.tools.external import register_external_tools
from app.agent.tools.external.dialogue import DialogueDeepSeekInput
from app.agent.tools.external.extraction import ExtractAnswersDeepSeekInput
from app.agent.tools.local import register_local_tools
from app.agent.tools.local.readiness import ReadinessCheckInput, ReadinessResult
from app.agent.tools.registry import ToolRegistry
from app.schemas.agent_protocol import AgentEvent, AgentRunResult, TerminalState
from app.schemas.agent_state import AgentState
from app.schemas.conversation import ConversationClientState
from app.schemas.extraction import ExtractionResult
from app.schemas.llm import LLMMessage
from app.services.deepseek_client import DeepSeekClient

MAX_AGENT_STEPS = 16


def _build_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    register_local_tools(registry)
    register_external_tools(registry)
    return registry


def _safe_error(msg: str) -> str:
    """安全文案：不泄露原始异常给用户。"""
    return "AI 暂时不可用，请稍后重试"


async def run_agent_event(
    state: AgentState,
    event: AgentEvent,
    registry: ToolRegistry | None = None,
    max_steps: int = MAX_AGENT_STEPS,
) -> AgentRunResult:
    if max_steps <= 0:
        return AgentRunResult(
            state=state,
            terminal=TerminalState.MAX_STEPS_EXCEEDED,
        )

    if event.type == "user_message":
        return await _handle_user_message(state, event, registry or _build_tool_registry())

    if event.type == "finish_requested":
        return await _handle_finish_requested(state, registry or _build_tool_registry())

    return AgentRunResult(state=state, terminal=TerminalState.FAILED)


async def _handle_user_message(
    state: AgentState,
    event: AgentEvent,
    registry: ToolRegistry,
) -> AgentRunResult:
    executor = ToolExecutor(registry)
    current = append_user_message(state, event.message)

    # Step 1: extraction
    extract_result = await executor.execute(
        "extract_answers.deepseek",
        ExtractAnswersDeepSeekInput(messages=current.messages),
    )
    if extract_result.error is None and isinstance(extract_result.data, ExtractionResult):
        current = apply_extraction_result(current, extract_result.data)
    else:
        current = current.model_copy(deep=True)
        current.validation_errors.append("extraction: AI 提取失败")

    # Step 2: readiness
    readiness_result = await executor.execute(
        "readiness.check",
        ReadinessCheckInput(answers=current.answers, branch=current.branch),
    )
    readiness: ReadinessResult | None = None
    if readiness_result.error is None and isinstance(readiness_result.data, ReadinessResult):
        readiness = readiness_result.data
        current = current.model_copy(deep=True)
        current.readiness_result = readiness

    # Step 3: dialogue
    missing_items = [m.model_dump() for m in readiness.missing_items] if readiness else []
    next_qs = readiness.next_questions if readiness else []
    dialogue_result = await executor.execute(
        "dialogue.deepseek",
        DialogueDeepSeekInput(
            messages=current.messages,
            missing_items=missing_items,
            next_questions=next_qs,
        ),
    )
    if dialogue_result.error is not None:
        current = append_assistant_message(current, _safe_error(""))
        return AgentRunResult(
            state=current,
            terminal=TerminalState.FAILED,
            response={"assistant_message": _safe_error("")},
        )

    assistant_text = dialogue_result.data.assistant_message
    current = append_assistant_message(current, assistant_text)

    resp: dict = {"assistant_message": assistant_text}
    if readiness:
        resp["readiness"] = readiness.model_dump()

    return AgentRunResult(
        state=current,
        terminal=TerminalState.AWAITING_USER,
        response=resp,
    )


async def _handle_finish_requested(
    state: AgentState,
    registry: ToolRegistry,
) -> AgentRunResult:
    executor = ToolExecutor(registry)
    result = await executor.execute(
        "readiness.check",
        ReadinessCheckInput(answers=state.answers, branch=state.branch),
    )
    if result.error is not None:
        return AgentRunResult(state=state, terminal=TerminalState.FAILED)

    readiness = result.data
    if not isinstance(readiness, ReadinessResult):
        return AgentRunResult(state=state, terminal=TerminalState.FAILED)

    new_state = state.model_copy(deep=True)
    new_state.readiness_result = readiness

    if readiness.unsupported_branch:
        return AgentRunResult(state=new_state, terminal=TerminalState.UNSUPPORTED_BRANCH)
    if not readiness.ready:
        return AgentRunResult(
            state=new_state,
            terminal=TerminalState.MISSING_INFO,
            response={"missing_items": [m.model_dump() for m in readiness.missing_items]},
        )
    return AgentRunResult(
        state=new_state,
        terminal=TerminalState.AWAITING_USER,
        response={"ready": True},
    )


async def run_agent_event_stream(
    state: AgentState,
    event: AgentEvent,
    registry: ToolRegistry | None = None,
) -> AsyncGenerator[dict, None]:
    if event.type != "user_message":
        result = await run_agent_event(state, event, registry)
        client_state = ConversationClientState.from_agent_state(result.state)
        yield {"type": "error", "message": "streaming 仅支持 user_message", "state": client_state.model_dump()}
        return

    tools = registry or _build_tool_registry()
    executor = ToolExecutor(tools)
    current = append_user_message(state, event.message)

    # extraction
    extract_result = await executor.execute(
        "extract_answers.deepseek",
        ExtractAnswersDeepSeekInput(messages=current.messages),
    )
    if extract_result.error is None and isinstance(extract_result.data, ExtractionResult):
        current = apply_extraction_result(current, extract_result.data)
    else:
        current = current.model_copy(deep=True)
        current.validation_errors.append("extraction: AI 提取失败")

    # readiness
    readiness_result = await executor.execute(
        "readiness.check",
        ReadinessCheckInput(answers=current.answers, branch=current.branch),
    )
    readiness: ReadinessResult | None = None
    if readiness_result.error is None and isinstance(readiness_result.data, ReadinessResult):
        readiness = readiness_result.data
        current = current.model_copy(deep=True)
        current.readiness_result = readiness

    # streaming dialogue
    missing_items = [m.model_dump() for m in readiness.missing_items] if readiness else []
    next_qs = readiness.next_questions if readiness else []

    from app.agent.tools.external.dialogue import _build_dialogue_prompt

    system_prompt = _build_dialogue_prompt(DialogueDeepSeekInput(
        messages=current.messages,
        missing_items=missing_items,
        next_questions=next_qs,
    ))
    llm_messages = [LLMMessage(role="system", content=system_prompt)]
    for msg in current.messages[-12:]:
        llm_messages.append(LLMMessage(role=msg.role, content=msg.content))

    assistant_text = ""
    try:
        client = DeepSeekClient()
        async for chunk in client.stream_chat(llm_messages, max_tokens=256, temperature=0.2):
            assistant_text += chunk
            yield {"type": "delta", "content": chunk}
    except Exception:
        cc = ConversationClientState.from_agent_state(current)
        yield {"type": "error", "message": _safe_error(""), "state": cc.model_dump()}
        return

    if not assistant_text.strip():
        cc = ConversationClientState.from_agent_state(current)
        yield {"type": "error", "message": _safe_error(""), "state": cc.model_dump()}
        return

    current = append_assistant_message(current, assistant_text)
    cc = ConversationClientState.from_agent_state(current)
    yield {"type": "done", "state": cc.model_dump()}
