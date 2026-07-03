import pytest

from app.agent.runner import _build_memory_query, run_agent_event, run_agent_event_stream
from app.agent.tools.base import ToolContext, ToolDefinition, ToolResult
from app.agent.tools.external import register_external_tools
from app.agent.tools.external.dialogue import DialogueDeepSeekInput
from app.agent.tools.external.extraction import ExtractAnswersDeepSeekInput
from app.agent.tools.local import register_local_tools
from app.agent.tools.local.readiness import ReadinessCheckInput, ReadinessResult
from app.agent.tools.registry import ToolRegistry
from app.schemas.agent_protocol import AgentEvent, TerminalState
from app.schemas.agent_state import AgentState
from app.schemas.extraction import ExtractionResult
from app.schemas.memory import MemoryEntry, MemoryFrontmatter, MemoryRecallInput, MemorySaveInput


def _full_registry() -> ToolRegistry:
    r = ToolRegistry()
    register_local_tools(r)
    register_external_tools(r)
    return r


# ── memory query helper ──

def test_build_memory_query_includes_slots():
    from app.schemas.slots import SlotValue
    state = AgentState()
    state.slots.industry = SlotValue(value="机械设备", confidence=0.9)
    state.slots.main_product = SlotValue(value="数控机床", confidence=0.9)
    query = _build_memory_query(state, "hello")
    assert "hello" in query
    assert "机械设备" in query
    assert "数控机床" in query


# ── user_message: explicit memory save ──

@pytest.mark.asyncio
async def test_user_message_remember_command_saves_memory_without_dialogue():
    captured = {}

    def _save_memory(inp, ctx):
        captured["input"] = inp
        from app.schemas.memory import MemorySaveOutput
        return ToolResult(data=MemorySaveOutput(path=".claude/memory/test.md", index_updated=True))

    r = ToolRegistry()
    r.register(ToolDefinition(
        name="memory.save",
        description="save",
        input_model=MemorySaveInput,
        handler=_save_memory,
    ))

    result = await run_agent_event(
        AgentState(),
        AgentEvent(type="user_message", message="/remember 用户偏好: 喜欢简洁中文回复"),
        r,
    )

    assert result.terminal == TerminalState.AWAITING_USER
    assert captured["input"].name == "用户偏好"
    assert captured["input"].content == "喜欢简洁中文回复"
    assert "已保存到长期记忆" in result.response["assistant_message"]


@pytest.mark.asyncio
async def test_user_message_remember_command_without_title_uses_content_prefix():
    captured = {}

    def _save_memory(inp, ctx):
        captured["input"] = inp
        from app.schemas.memory import MemorySaveOutput
        return ToolResult(data=MemorySaveOutput(path=".claude/memory/test.md", index_updated=True))

    r = ToolRegistry()
    r.register(ToolDefinition(
        name="memory.save",
        description="save",
        input_model=MemorySaveInput,
        handler=_save_memory,
    ))

    result = await run_agent_event(
        AgentState(),
        AgentEvent(type="user_message", message="/remember 用户希望优先追问关键问题"),
        r,
    )

    assert result.terminal == TerminalState.AWAITING_USER
    assert captured["input"].name == "用户希望优先追问关键问题"
    assert captured["input"].content == "用户希望优先追问关键问题"


@pytest.mark.asyncio
async def test_stream_remember_command_saves_memory_without_llm():
    captured = {}

    def _save_memory(inp, ctx):
        captured["input"] = inp
        from app.schemas.memory import MemorySaveOutput
        return ToolResult(data=MemorySaveOutput(path=".claude/memory/test.md", index_updated=True))

    r = ToolRegistry()
    r.register(ToolDefinition(
        name="memory.save",
        description="save",
        input_model=MemorySaveInput,
        handler=_save_memory,
    ))

    events = [
        e async for e in run_agent_event_stream(
            AgentState(),
            AgentEvent(type="user_message", message="/remember 项目目标: 做真实 Agent 产品"),
            r,
        )
    ]

    assert captured["input"].name == "项目目标"
    assert captured["input"].content == "做真实 Agent 产品"
    assert events[0]["type"] == "delta"
    assert "已保存到长期记忆" in events[0]["content"]
    assert events[-1]["type"] == "done"


# ── user_message: memory recall 调用 ──

@pytest.mark.asyncio
async def test_user_message_calls_memory_recall_before_dialogue():
    """memory.recall 在 dialogue.deepseek 之前被调用。"""
    call_order = []

    def _fake_readiness(inp, ctx):
        return ToolResult(data=ReadinessResult(ready=False, missing_items=[]))

    def _fake_extract(inp, ctx):
        return ToolResult(data=ExtractionResult())

    def _track_memory(inp, ctx):
        call_order.append("memory.recall")
        return ToolResult(data=type("X", (), {"entries": []})())

    def _track_dialogue(inp, ctx):
        call_order.append("dialogue.deepseek")
        from app.agent.tools.external.dialogue import DialogueDeepSeekOutput
        return ToolResult(data=DialogueDeepSeekOutput(assistant_message="ok"))

    r = ToolRegistry()
    r.register(ToolDefinition(name="extract_answers.deepseek", description="e", input_model=ExtractAnswersDeepSeekInput, handler=_fake_extract))
    r.register(ToolDefinition(name="readiness.check", description="r", input_model=ReadinessCheckInput, handler=_fake_readiness))
    r.register(ToolDefinition(name="memory.recall", description="m", input_model=MemoryRecallInput, handler=_track_memory))
    r.register(ToolDefinition(name="dialogue.deepseek", description="d", input_model=DialogueDeepSeekInput, handler=_track_dialogue))

    state = AgentState()
    result = await run_agent_event(state, AgentEvent(type="user_message", message="hello"), r)
    assert result.terminal == TerminalState.AWAITING_USER
    mem_idx = call_order.index("memory.recall")
    dia_idx = call_order.index("dialogue.deepseek")
    assert mem_idx < dia_idx, f"memory.recall 应在 dialogue 之前, order={call_order}"


@pytest.mark.asyncio
async def test_user_message_passes_memory_entries_to_dialogue():
    """memory.recall 返回的 entries 被传入 dialogue.deepseek。"""
    dummy_entry = MemoryEntry(
        path=".claude/memory/test.md",
        frontmatter=MemoryFrontmatter(name="测试记忆", description="desc", type="user"),
        content="test content",
    )
    captured_input = {}

    def _fake_readiness(inp, ctx):
        return ToolResult(data=ReadinessResult(ready=False, missing_items=[]))

    def _fake_extract(inp, ctx):
        return ToolResult(data=ExtractionResult())

    def _fake_memory(inp, ctx):
        return ToolResult(data=type("X", (), {"entries": [dummy_entry]})())

    def _capture_dialogue(inp, ctx):
        captured_input["memory_entries"] = inp.memory_entries
        from app.agent.tools.external.dialogue import DialogueDeepSeekOutput
        return ToolResult(data=DialogueDeepSeekOutput(assistant_message="ok"))

    r = ToolRegistry()
    r.register(ToolDefinition(name="extract_answers.deepseek", description="e", input_model=ExtractAnswersDeepSeekInput, handler=_fake_extract))
    r.register(ToolDefinition(name="readiness.check", description="r", input_model=ReadinessCheckInput, handler=_fake_readiness))
    r.register(ToolDefinition(name="memory.recall", description="m", input_model=MemoryRecallInput, handler=_fake_memory))
    r.register(ToolDefinition(name="dialogue.deepseek", description="d", input_model=DialogueDeepSeekInput, handler=_capture_dialogue))

    state = AgentState()
    result = await run_agent_event(state, AgentEvent(type="user_message", message="hello"), r)
    assert result.terminal == TerminalState.AWAITING_USER
    assert len(captured_input["memory_entries"]) == 1
    assert captured_input["memory_entries"][0].frontmatter.name == "测试记忆"


@pytest.mark.asyncio
async def test_user_message_memory_recall_error_does_not_break_flow():
    """memory.recall 失败时仍继续 dialogue。"""
    def _fake_readiness(inp, ctx):
        return ToolResult(data=ReadinessResult(ready=False, missing_items=[]))

    def _fake_extract(inp, ctx):
        return ToolResult(data=ExtractionResult())

    def _fail_memory(inp, ctx):
        from app.agent.tools.base import ToolError, ToolErrorCode
        return ToolResult(error=ToolError(code=ToolErrorCode.TRANSIENT, message="fail", retryable=True))

    captured_memory_entries = {}
    def _capture_dialogue(inp, ctx):
        captured_memory_entries["entries"] = inp.memory_entries
        from app.agent.tools.external.dialogue import DialogueDeepSeekOutput
        return ToolResult(data=DialogueDeepSeekOutput(assistant_message="ok"))

    r = ToolRegistry()
    r.register(ToolDefinition(name="extract_answers.deepseek", description="e", input_model=ExtractAnswersDeepSeekInput, handler=_fake_extract))
    r.register(ToolDefinition(name="readiness.check", description="r", input_model=ReadinessCheckInput, handler=_fake_readiness))
    r.register(ToolDefinition(name="memory.recall", description="m", input_model=MemoryRecallInput, handler=_fail_memory))
    r.register(ToolDefinition(name="dialogue.deepseek", description="d", input_model=DialogueDeepSeekInput, handler=_capture_dialogue))

    state = AgentState()
    result = await run_agent_event(state, AgentEvent(type="user_message", message="hello"), r)
    assert result.terminal == TerminalState.AWAITING_USER
    assert captured_memory_entries["entries"] == []


# ── finish_requested ──

@pytest.mark.asyncio
async def test_finish_requested_missing_q5_missing_info():
    state = AgentState()
    result = await run_agent_event(state, AgentEvent(type="finish_requested"))
    assert result.terminal == TerminalState.MISSING_INFO


@pytest.mark.asyncio
async def test_finish_requested_inexperienced_unsupported():
    state = AgentState(answers={"Q5": ["D"]}, branch="inexperienced")
    result = await run_agent_event(state, AgentEvent(type="finish_requested"))
    assert result.terminal == TerminalState.UNSUPPORTED_BRANCH


@pytest.mark.asyncio
async def test_max_steps_zero_returns_exceeded():
    state = AgentState()
    result = await run_agent_event(state, AgentEvent(type="user_message", message="hello"), max_steps=0)
    assert result.terminal == TerminalState.MAX_STEPS_EXCEEDED


@pytest.mark.asyncio
async def test_finish_requested_missing_q5_no_registry_needed():
    state = AgentState(answers={}, branch=None)
    r = ToolRegistry()
    register_local_tools(r)
    from app.agent.tools.external.extraction import ExtractAnswersDeepSeekInput
    from app.agent.tools.base import ToolDefinition
    r.register(ToolDefinition(name="extract_answers.deepseek", description="e", input_model=ExtractAnswersDeepSeekInput, handler=lambda i, c: ToolResult(data=ExtractionResult())))
    result = await run_agent_event(state, AgentEvent(type="finish_requested"), registry=r)
    assert result.terminal == TerminalState.MISSING_INFO
