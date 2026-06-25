from app.agent.extraction import QUESTION_CATALOG
from app.agent.nodes import apply_extraction_result
from app.schemas.agent_state import AgentState
from app.schemas.extraction import ExtractedAnswer, ExtractedSlot, ExtractionResult
from app.schemas.slots import SlotValue


def _state(**kwargs) -> AgentState:
    return AgentState(**kwargs)


# ── catalog 完整性 ─────────────────────────────────────────────

def test_question_catalog_contains_full_experienced_questions():
    assert "Q31" in QUESTION_CATALOG
    assert "Q29" in QUESTION_CATALOG
    assert "Q26" in QUESTION_CATALOG
    assert "Q18" in QUESTION_CATALOG
    assert "Q6" in QUESTION_CATALOG
    assert "Q2a" in QUESTION_CATALOG
    # Q1 不进 answers，但不排除 Q10/Q11/Q12 等
    assert not any(line.startswith("Q1 ") for line in QUESTION_CATALOG.split("\n"))


# ── 槽位安全合并 ───────────────────────────────────────────────

def test_unknown_slot_field_not_written_and_logs_error():
    extraction = ExtractionResult(
        slots={"not_a_field": ExtractedSlot(value="x", confidence=0.9)}
    )
    result = apply_extraction_result(_state(), extraction)
    assert result.slots.company_name is None
    assert any("忽略槽位" in e for e in result.validation_errors)


def test_low_confidence_slot_does_not_overwrite_existing():
    state = _state(slots={"industry": SlotValue(value="健身器材", confidence=0.9)})
    extraction = ExtractionResult(
        slots={"industry": ExtractedSlot(value="服装", confidence=0.5)}
    )
    result = apply_extraction_result(state, extraction)
    assert result.slots.industry.value == "健身器材"
    assert any("低置信槽位" in e for e in result.validation_errors)


# ── answers 校验 ───────────────────────────────────────────────

def test_invalid_question_id_not_written():
    extraction = ExtractionResult(
        answers=[ExtractedAnswer(question_id="Q99", option_ids=["A"], confidence=0.9)]
    )
    result = apply_extraction_result(_state(), extraction)
    assert "Q99" not in result.answers


def test_invalid_option_id_not_written():
    extraction = ExtractionResult(
        answers=[ExtractedAnswer(question_id="Q2a", option_ids=["Z"], confidence=0.9)]
    )
    result = apply_extraction_result(_state(), extraction)
    assert "Q2a" not in result.answers


def test_single_choice_multi_select_not_written():
    extraction = ExtractionResult(
        answers=[ExtractedAnswer(question_id="Q2a", option_ids=["A", "B"], confidence=0.9)]
    )
    result = apply_extraction_result(_state(), extraction)
    assert "Q2a" not in result.answers


def test_valid_q5_written_and_branch_set():
    extraction = ExtractionResult(
        answers=[ExtractedAnswer(question_id="Q5", option_ids=["C"], confidence=0.9)]
    )
    result = apply_extraction_result(_state(), extraction)
    assert result.answers["Q5"] == ["C"]
    assert result.branch == "experienced"


def test_q1_not_in_answers():
    """Q1 开放题，catalog 中无 Q1，即便出现在 answers 也不写入"""
    extraction = ExtractionResult(
        answers=[ExtractedAnswer(question_id="Q1", option_ids=["健身器材"], confidence=0.9)]
    )
    result = apply_extraction_result(_state(), extraction)
    assert "Q1" not in result.answers


def test_q1_empty_option_ids_not_written():
    """open_text 题目 option_ids=[] 也不写入 answers"""
    extraction = ExtractionResult(
        answers=[ExtractedAnswer(question_id="Q1", option_ids=[], confidence=0.9)]
    )
    result = apply_extraction_result(_state(), extraction)
    assert "Q1" not in result.answers
    assert any("开放题" in e or "未知题号" in e for e in result.validation_errors)


# ── branch 隔离：Q5=D 拒绝 experienced 题目 ─────────────────────

def test_q5_d_rejects_experienced_questions():
    extraction = ExtractionResult(
        answers=[
            ExtractedAnswer(question_id="Q5", option_ids=["D"], confidence=0.9),
            ExtractedAnswer(question_id="Q6", option_ids=["A"], confidence=0.9),
        ]
    )
    result = apply_extraction_result(_state(), extraction)
    assert result.branch == "inexperienced"
    assert "Q5" in result.answers
    assert "Q6" not in result.answers
    assert any("分支不允许" in e for e in result.validation_errors)


def test_q5_d_preserves_state_branch_and_rejects_q7():
    state = _state(branch="inexperienced")
    extraction = ExtractionResult(
        answers=[
            ExtractedAnswer(question_id="Q7", option_ids=["A"], confidence=0.9),
        ]
    )
    result = apply_extraction_result(state, extraction)
    assert result.branch == "inexperienced"
    assert "Q7" not in result.answers


# ── answer confidence 过滤 ─────────────────────────────────────

def test_low_confidence_answer_not_written():
    extraction = ExtractionResult(
        answers=[ExtractedAnswer(question_id="Q2a", option_ids=["A"], confidence=0.3)]
    )
    result = apply_extraction_result(_state(), extraction)
    assert "Q2a" not in result.answers
    assert any("低置信答案" in e for e in result.validation_errors)


def test_low_confidence_q5_not_set_branch():
    extraction = ExtractionResult(
        answers=[ExtractedAnswer(question_id="Q5", option_ids=["C"], confidence=0.3)]
    )
    result = apply_extraction_result(_state(), extraction)
    assert "Q5" not in result.answers
    assert result.branch is None

