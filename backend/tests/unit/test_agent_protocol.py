import pytest
from pydantic import ValidationError

from app.schemas.agent_protocol import AgentEvent, AgentRunResult, TerminalState
from app.schemas.agent_state import AgentState


# ── TerminalState ──

def test_terminal_state_all_values():
    expected = {
        "awaiting_user",
        "missing_info",
        "unsupported_branch",
        "completed",
        "completed_with_template",
        "failed",
        "aborted",
        "max_steps_exceeded",
    }
    actual = set(TerminalState.__members__.values())
    assert actual == expected


# ── AgentEvent ──

def test_agent_event_user_message_strips():
    ev = AgentEvent(type="user_message", message=" hello ")
    assert ev.message == "hello"


def test_agent_event_user_message_rejects_empty():
    with pytest.raises(ValidationError):
        AgentEvent(type="user_message", message="")


def test_agent_event_user_message_rejects_whitespace_only():
    with pytest.raises(ValidationError):
        AgentEvent(type="user_message", message="   ")


def test_agent_event_user_message_rejects_over_500():
    with pytest.raises(ValidationError):
        AgentEvent(type="user_message", message="x" * 501)


def test_agent_event_user_message_accepts_500():
    ev = AgentEvent(type="user_message", message="x" * 500)
    assert len(ev.message) == 500


def test_agent_event_finish_requested_without_message():
    ev = AgentEvent(type="finish_requested")
    assert ev.message is None


def test_agent_event_finish_requested_with_message():
    ev = AgentEvent(type="finish_requested", message="生成报告")
    assert ev.message == "生成报告"


# ── AgentRunResult ──

def test_agent_run_result_serializable():
    state = AgentState()
    r = AgentRunResult(
        state=state,
        terminal=TerminalState.AWAITING_USER,
        response={"type": "awaiting_user"},
    )
    d = r.model_dump()
    assert d["terminal"] == "awaiting_user"
    assert isinstance(d["state"], dict)
