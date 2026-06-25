import pytest

from app.schemas.agent_state import AgentState
from app.agent.state_machine import (
    append_assistant_message,
    append_user_message,
    decide_branch_from_q5,
    is_ready_to_score,
    register_ai_failure,
    should_stop_conversation,
    trim_message_history,
)


def _fresh_state(**kwargs) -> AgentState:
    return AgentState(**kwargs)


# ── 轮次控制 ───────────────────────────────────────────────────

def test_append_user_message_increments_round():
    state = _fresh_state()
    new_state = append_user_message(state, "你好")
    assert new_state.conversation_round == 1
    assert new_state.messages[-1].role == "user"
    assert new_state.messages[-1].content == "你好"


def test_append_user_message_rejects_empty():
    state = _fresh_state()
    with pytest.raises(ValueError):
        append_user_message(state, "   ")


def test_append_assistant_does_not_increment_round():
    state = _fresh_state()
    new_state = append_assistant_message(state, "你好，我是诊断顾问")
    assert new_state.conversation_round == 0
    assert new_state.messages[-1].role == "assistant"


def test_should_stop_at_max_rounds():
    state = _fresh_state(conversation_round=7, max_rounds=8)
    assert not should_stop_conversation(state)
    state = _fresh_state(conversation_round=8, max_rounds=8)
    assert should_stop_conversation(state)


# ── 不可变性 ───────────────────────────────────────────────────

def test_append_user_message_does_not_mutate_original():
    original = _fresh_state()
    append_user_message(original, "你好")
    assert original.conversation_round == 0
    assert original.messages == []


def test_register_ai_failure_does_not_mutate_original():
    original = _fresh_state()
    register_ai_failure(original, "err")
    assert original.ai_failure_count == 0
    assert original.validation_errors == []


def test_trim_message_history_does_not_mutate_original():
    from app.schemas.agent_state import AgentMessage
    original = _fresh_state()
    for i in range(15):
        original.messages.append(AgentMessage(role="user", content=f"msg {i}"))
    trimmed = trim_message_history(original, max_messages=5)
    assert len(original.messages) == 15
    assert len(trimmed.messages) == 5


# ── 失败兜底 ───────────────────────────────────────────────────

def test_register_ai_failure_tracks_count():
    state = _fresh_state()
    state = register_ai_failure(state, "timeout")
    assert state.ai_failure_count == 1
    assert "timeout" in state.validation_errors


def test_register_ai_failure_two_triggers_fallback():
    state = _fresh_state(max_ai_failures=2)
    state = register_ai_failure(state, "timeout 1")
    state = register_ai_failure(state, "timeout 2")
    assert state.status == "fallback_questionnaire"
    assert state.ai_failure_count == 2


# ── 分支判断 ───────────────────────────────────────────────────

def test_q5_abc_routes_to_experienced():
    for opt in ("A", "B", "C"):
        state = _fresh_state(answers={"Q5": [opt]})
        new_state = decide_branch_from_q5(state)
        assert new_state.branch == "experienced"


def test_q5_d_routes_to_inexperienced():
    state = _fresh_state(answers={"Q5": ["D"]})
    new_state = decide_branch_from_q5(state)
    assert new_state.branch == "inexperienced"


def test_q5_missing_does_not_change_branch():
    state = _fresh_state(branch=None, answers={})
    new_state = decide_branch_from_q5(state)
    assert new_state.branch is None


def test_q5_invalid_option_logs_error():
    state = _fresh_state(answers={"Q5": ["Z"]})
    new_state = decide_branch_from_q5(state)
    assert len(new_state.validation_errors) > 0


def test_q5_invalid_clears_old_branch():
    state = _fresh_state(branch="experienced", answers={"Q5": ["Z"]})
    new_state = decide_branch_from_q5(state)
    assert new_state.branch is None
    assert len(new_state.validation_errors) > 0


def test_q5_multi_select_clears_branch():
    state = _fresh_state(branch="experienced", answers={"Q5": ["A", "B"]})
    new_state = decide_branch_from_q5(state)
    assert new_state.branch is None


# ── 评分就绪判断 ───────────────────────────────────────────────

def test_ready_to_score_experienced_with_enough_answers():
    state = _fresh_state(
        branch="experienced",
        answers={"Q1": ["x"], "Q2a": ["A"], "Q3a": ["A"], "Q4": ["A"],
                  "Q5": ["A"], "Q6": ["A"], "Q7": ["A"], "Q8": ["A"]},
    )
    assert is_ready_to_score(state)


def test_ready_to_score_requires_active_status():
    state = _fresh_state(branch="experienced", status="completed",
                          answers={f"Q{i}": ["A"] for i in range(1, 10)})
    assert not is_ready_to_score(state)


def test_ready_to_score_requires_experienced_branch():
    state = _fresh_state(branch="inexperienced",
                          answers={f"Q{i}": ["A"] for i in range(1, 10)})
    assert not is_ready_to_score(state)


def test_ready_to_score_requires_q5():
    state = _fresh_state(branch="experienced",
                          answers={f"Q{i}": ["A"] for i in [1, 2, 3, 4, 6, 7, 8, 9]})
    assert not is_ready_to_score(state)


def test_ready_to_score_requires_min_answers():
    state = _fresh_state(branch="experienced", answers={"Q5": ["A"]})
    assert not is_ready_to_score(state)


def test_ready_to_score_rejects_validation_errors():
    state = _fresh_state(
        branch="experienced",
        validation_errors=["Q5 无效"],
        answers={"Q1": ["x"], "Q2a": ["A"], "Q3a": ["A"], "Q4": ["A"],
                  "Q5": ["A"], "Q6": ["A"], "Q7": ["A"], "Q8": ["A"]},
    )
    assert not is_ready_to_score(state)


# ── 消息历史裁剪 ───────────────────────────────────────────────

def test_trim_message_history_keeps_last_12():
    from app.schemas.agent_state import AgentMessage

    state = _fresh_state()
    for i in range(20):
        state.messages.append(AgentMessage(role="user", content=f"msg {i}"))
    trimmed = trim_message_history(state, max_messages=12)
    assert len(trimmed.messages) == 12
    assert trimmed.messages[0].content == "msg 8"
    assert trimmed.messages[-1].content == "msg 19"
