from app.agent.extraction import QUESTION_CATALOG
from app.agent.nodes import _apply_q30_intent_patch, apply_extraction_result
from app.schemas.agent_state import AgentState, AgentMessage
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


# ── extraction history_window ──
import pytest
from app.agent.extraction import extract_from_messages
from app.schemas.agent_state import AgentMessage


@pytest.mark.asyncio
async def test_extract_from_messages_uses_default_history_window(monkeypatch):
    """默认 history_window=12，只提取最近 12 条。"""
    recorded_texts = []

    class FakeClient:
        async def chat_json(self, messages, response_model, max_tokens, temperature):
            recorded_texts.append(messages[-1].content)
            return ExtractionResult()

    monkeypatch.setattr("app.agent.extraction.DeepSeekClient", lambda: FakeClient())

    messages = [AgentMessage(role="user", content=f"msg{i}") for i in range(20)]
    await extract_from_messages(messages)
    user_text = recorded_texts[0]
    assert "msg19" in user_text
    assert "msg0" not in user_text  # 20 - 12 = 8, only msg8..msg19


@pytest.mark.asyncio
async def test_extract_from_messages_history_window_none_uses_all_messages(monkeypatch):
    """history_window=None 使用完整 messages。"""
    recorded_texts = []

    class FakeClient:
        async def chat_json(self, messages, response_model, max_tokens, temperature):
            recorded_texts.append(messages[-1].content)
            return ExtractionResult()

    monkeypatch.setattr("app.agent.extraction.DeepSeekClient", lambda: FakeClient())

    messages = [AgentMessage(role="user", content=f"msg{i}") for i in range(20)]
    await extract_from_messages(messages, history_window=None)
    user_text = recorded_texts[0]
    assert "msg0" in user_text
    assert "msg19" in user_text


# ── Q30 intent patch ──

def test_q30_intent_patch_maps_increase_shipments():
    """用户说'希望提高我的出货量' → Q30 被自动写入选项 A。"""
    state = AgentState(
        messages=[
            AgentMessage(role="user", content="希望提高我的出货量"),
        ],
        answers={},
        branch="experienced",
    )
    extraction = ExtractionResult(slots={}, answers=[])
    _apply_q30_intent_patch(state, extraction)
    assert state.answers.get("Q30") == ["A"]


def test_q30_intent_patch_skips_when_q30_already_exists():
    """已有 Q30 答案时不覆盖。"""
    state = AgentState(
        messages=[AgentMessage(role="user", content="希望提高出货量")],
        answers={"Q30": ["E"]},
        branch="experienced",
    )
    extraction = ExtractionResult(slots={}, answers=[])
    _apply_q30_intent_patch(state, extraction)
    assert state.answers["Q30"] == ["E"]


def test_q30_intent_patch_skips_inexperienced_branch():
    """inexperienced 分支不触发 Q30 patch。"""
    state = AgentState(
        messages=[AgentMessage(role="user", content="希望提高出货量")],
        answers={},
        branch="inexperienced",
    )
    extraction = ExtractionResult(slots={}, answers=[])
    _apply_q30_intent_patch(state, extraction)
    assert "Q30" not in state.answers


def test_readiness_no_missing_q30_after_intent_patch():
    """构造包含 Q5/Q8/Q17/Q19/Q31 + '希望提高出货量' 的状态，验证 readiness 不再缺 Q30。"""
    from app.agent.tools.local.readiness import ReadinessCheckInput, readiness_check_handler
    from app.agent.tools.base import ToolContext

    state = AgentState(
        messages=[AgentMessage(role="user", content="希望提高出货量")],
        answers={"Q5": ["C"], "Q8": ["B"], "Q17": ["A"], "Q19": ["B"], "Q31": ["A"]},
        branch="experienced",
    )
    extraction = ExtractionResult(slots={}, answers=[])
    _apply_q30_intent_patch(state, extraction)

    result = readiness_check_handler(
        ReadinessCheckInput(answers=state.answers, branch=state.branch),
        ToolContext(),
    )
    rr = result.data
    q30_missing = [m for m in rr.missing_items if m.question_id == "Q30"]
    assert len(q30_missing) == 0, f"Q30 should not be missing, got {q30_missing}"

