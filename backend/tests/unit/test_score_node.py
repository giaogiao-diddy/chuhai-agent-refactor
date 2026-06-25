from app.agent.nodes import score_node
from app.schemas.agent_state import AgentState
from app.schemas.slots import SlotValue


def _state(**kwargs) -> AgentState:
    return AgentState(**kwargs)


def test_score_node_scores_experienced_answers():
    state = _state(
        branch="experienced",
        slots={
            "industry": SlotValue(value="健身器材", confidence=0.9),
            "main_product": SlotValue(value="力量训练设备", confidence=0.9),
        },
        answers={
            "Q2a": ["A"], "Q2b": ["B"], "Q3a": ["B"], "Q3b": ["B"],
            "Q4": ["A"], "Q5": ["C"], "Q6": ["B", "C"], "Q7": ["C"],
        },
    )
    result = score_node(state)
    assert result.scoring_result is not None
    assert 0 <= result.scoring_result.feasibility_score <= 100
    assert 0 <= result.scoring_result.lead_score <= 100
    assert result.scoring_result.tag
    assert result.scoring_result.lead_priority
    assert result.status == "ready_to_score"
    assert result.scoring_error is None


def test_score_node_rejects_inexperienced_branch():
    state = _state(branch="inexperienced", answers={"Q5": ["D"]})
    result = score_node(state)
    assert result.scoring_result is None
    assert result.scoring_error
    assert any("非 experienced" in e for e in result.validation_errors)


def test_score_node_rejects_insufficient_answers():
    state = _state(
        branch="experienced",
        slots={
            "industry": SlotValue(value="健身器材", confidence=0.9),
            "main_product": SlotValue(value="力量训练设备", confidence=0.9),
        },
        answers={"Q5": ["C"]},  # only 1 answer, need >=8
    )
    result = score_node(state)
    assert result.scoring_result is None
    assert result.status != "ready_to_score"
    assert result.scoring_error


def test_score_node_skips_when_validation_errors_exist():
    state = _state(
        branch="experienced",
        answers={"Q5": ["C"]},
        validation_errors=["已有错误"],
    )
    result = score_node(state)
    assert result.scoring_result is None
    assert result.scoring_error


def test_score_node_records_invalid_answer_error():
    # 需要 >=8 答案越过 is_ready_to_score，才能触发 build_scoring_input 的报错
    state = _state(
        branch="experienced",
        slots={
            "industry": SlotValue(value="健身器材", confidence=0.9),
            "main_product": SlotValue(value="力量训练设备", confidence=0.9),
        },
        answers={
            "Q5": ["C"], "Q2a": ["Z"], "Q2b": ["B"], "Q3a": ["B"],
            "Q3b": ["B"], "Q4": ["A"], "Q6": ["B"], "Q7": ["C"],
        },
    )
    result = score_node(state)
    assert result.scoring_result is None
    assert result.scoring_error
    assert any("score_node" in e for e in result.validation_errors)
