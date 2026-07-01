import pytest

from app.agent.runner import run_agent_event
from app.agent.tools.external import register_external_tools
from app.agent.tools.local import register_local_tools
from app.agent.tools.registry import ToolRegistry
from app.schemas.agent_protocol import AgentEvent, TerminalState
from app.schemas.agent_state import AgentState


def _full_registry() -> ToolRegistry:
    r = ToolRegistry()
    register_local_tools(r)
    register_external_tools(r)
    return r


# ── user_message (non-AI, monkeypatch) ──

@pytest.mark.asyncio
async def test_user_message_event_append_only_no_ai():
    """不使用真实 AI 时 user_message 路径由 fixture registry 控制。
    这里只验证 runner 正确路由到 user_message 分支并尝试调用工具。
    工具未注册时会抛 KeyError（预期行为——表明路径正确）。
    """
    state = AgentState()
    r = ToolRegistry()  # 空 registry，无任何工具
    with pytest.raises(KeyError):  # 尝试调 extract_answers.deepseek 会失败
        await run_agent_event(
            state, AgentEvent(type="user_message", message="你好"),
            registry=r,
        )


# ── finish_requested: 信息不足 ──

@pytest.mark.asyncio
async def test_finish_requested_missing_q5_missing_info():
    state = AgentState()
    result = await run_agent_event(
        state, AgentEvent(type="finish_requested"),
    )
    assert result.terminal == TerminalState.MISSING_INFO
    assert result.state.readiness_result.ready is False
    assert any(m.question_id == "Q5" for m in result.state.readiness_result.missing_items)
    assert result.state.scoring_result is None
    assert result.state.user_report is None


# ── finish_requested: inexperienced ──

@pytest.mark.asyncio
async def test_finish_requested_inexperienced_unsupported():
    state = AgentState(
        answers={"Q5": ["D"]},
        branch="inexperienced",
    )
    result = await run_agent_event(
        state, AgentEvent(type="finish_requested"),
    )
    assert result.terminal == TerminalState.UNSUPPORTED_BRANCH
    assert result.state.readiness_result.unsupported_branch is True
    assert result.state.scoring_result is None


# ── max_steps_exceeded ──

@pytest.mark.asyncio
async def test_max_steps_zero_returns_exceeded():
    state = AgentState()
    result = await run_agent_event(
        state, AgentEvent(type="user_message", message="hello"),
        max_steps=0,
    )
    assert result.terminal == TerminalState.MAX_STEPS_EXCEEDED
    assert result.state.conversation_round == 0


# ── finish_requested: ready 但本 Phase 不继续 ──

@pytest.mark.asyncio
async def test_finish_requested_ready_but_phase_does_not_continue():
    answers = {
        "Q5": ["A"], "Q6": ["A"], "Q8": ["A"], "Q11": ["A"],
        "Q17": ["A"], "Q19": ["A"], "Q22": ["A"], "Q30": ["A"],
        "Q31": ["A"],
    }
    state = AgentState(answers=answers, branch="experienced")
    result = await run_agent_event(
        state, AgentEvent(type="finish_requested"),
    )
    assert result.terminal == TerminalState.AWAITING_USER
    assert result.response is not None
    assert result.response["ready"] is True
    assert result.state.scoring_result is None
    assert result.state.user_report is None
