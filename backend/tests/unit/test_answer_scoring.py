# answer_scoring.py 单元测试：逐题计分 / 归一化 / 管道 / 边界

import pytest

from app.scoring.answer_scoring import (
    DIM_RAW_MAX_F,
    DIM_RAW_MAX_L,
    build_scoring_input,
    normalize_dimensions,
    score_answers,
    score_q1_information_completeness,
)
from app.scoring.engine import calculate_scoring
from app.scoring.rules import FEASIBILITY_WEIGHTS, LEAD_WEIGHTS
from app.schemas.slots import CompanySlots, SlotValue


def _slots(*, industry: str | None, product: str | None) -> CompanySlots:
    return CompanySlots(
        industry=SlotValue(value=industry, confidence=1.0) if industry else None,
        main_product=SlotValue(value=product, confidence=1.0) if product else None,
    )


# ── Q1 信息完整度 ──────────────────────────────────────────────

def test_q1_both_present_gets_full_score():
    slots = _slots(industry="健身器材", product="家用力量训练设备")
    f, l = score_q1_information_completeness(slots)
    assert f == 2.0
    assert l == 3.0


def test_q1_only_industry_gets_partial():
    slots = _slots(industry="健身器材", product=None)
    f, l = score_q1_information_completeness(slots)
    assert f == 1.0
    assert l == 1.0


def test_q1_only_product_gets_partial():
    slots = _slots(industry=None, product="家用力量训练设备")
    f, l = score_q1_information_completeness(slots)
    assert f == 1.0
    assert l == 1.0


def test_q1_neither_gets_zero():
    slots = _slots(industry=None, product=None)
    f, l = score_q1_information_completeness(slots)
    assert f == 0.0
    assert l == 0.0


def test_q1_empty_strings_count_as_missing():
    slots = CompanySlots(
        industry=SlotValue(value="  ", confidence=1.0),
        main_product=SlotValue(value="", confidence=1.0),
    )
    f, l = score_q1_information_completeness(slots)
    assert f == 0.0
    assert l == 0.0


# ── 逐题计分 ───────────────────────────────────────────────────

def test_single_choice_adds_option_score():
    f_raw, l_raw = score_answers({"Q2a": ["A"]})
    assert f_raw["enterprise_base"] == 3.0
    assert l_raw["enterprise_base"] == 2.0


def test_multiple_choice_sums_with_cap():
    f_raw, l_raw = score_answers({"Q11": ["A", "C"]})
    assert f_raw["product_supply_chain"] == 3.0
    assert l_raw["product_supply_chain"] == 2.0


def test_multiple_choice_under_cap():
    f_raw, l_raw = score_answers({"Q11": ["A"]})
    assert f_raw["product_supply_chain"] == 3.0
    assert l_raw["product_supply_chain"] == 2.0


def test_q26_accumulates_fractional_scores():
    f_raw, l_raw = score_answers({"Q26": ["A", "B", "C"]})
    assert f_raw["content_fitness"] == pytest.approx(0.9)
    assert l_raw["content_fitness"] == pytest.approx(1.2)


def test_q26_all_nine_options_accumulated():
    all_nine = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
    f_raw, l_raw = score_answers({"Q26": all_nine})
    assert f_raw["content_fitness"] == pytest.approx(2.7)
    assert l_raw["content_fitness"] == pytest.approx(3.6)


def test_empty_answers_gives_zero():
    f_raw, l_raw = score_answers({})
    assert all(v == 0.0 for v in f_raw.values())
    assert all(v == 0.0 for v in l_raw.values())


def test_multiple_questions_accumulate_dimension():
    f_raw, l_raw = score_answers({"Q2a": ["A"], "Q2b": ["A"]})
    assert f_raw["enterprise_base"] == 6.0
    assert l_raw["enterprise_base"] == 5.0


def test_q1_included_when_slots_provided():
    slots = _slots(industry="健身器材", product="力量训练设备")
    f_raw, l_raw = score_answers({"Q2a": ["A"]}, q1_slots=slots)
    assert f_raw["enterprise_base"] == 5.0
    assert l_raw["enterprise_base"] == 5.0


def test_q5_d_zero_scores():
    f_raw, l_raw = score_answers({"Q5": ["D"]})
    assert f_raw["overseas_validation"] == 0.0
    assert l_raw["overseas_validation"] == 0.0


# ── 边界：拒绝 ─────────────────────────────────────────────────

def test_unknown_question_id_raises():
    with pytest.raises(ValueError, match="未知题号"):
        score_answers({"NONEXISTENT": ["A"]})


def test_invalid_option_id_raises():
    with pytest.raises(ValueError, match="无效选项"):
        score_answers({"Q2a": ["Z"]})


def test_single_choice_multi_select_raises():
    with pytest.raises(ValueError, match="单选题"):
        score_answers({"Q2a": ["A", "B"]})


def test_inexperienced_branch_rejects_experienced_questions():
    with pytest.raises(ValueError, match="inexperienced 分支") as exc_info:
        score_answers({"Q6": ["A"]}, branch="inexperienced")


# ── 归一化 ─────────────────────────────────────────────────────

def test_normalize_perfect_score_gives_header_weight():
    f_raw = {dim: DIM_RAW_MAX_F.get(dim, 20) for dim in FEASIBILITY_WEIGHTS}
    l_raw = {dim: DIM_RAW_MAX_L.get(dim, 20) for dim in LEAD_WEIGHTS}
    f_norm, l_norm = normalize_dimensions(f_raw, l_raw)
    for dim, header in FEASIBILITY_WEIGHTS.items():
        assert f_norm[dim] == header
    for dim, header in LEAD_WEIGHTS.items():
        assert l_norm[dim] == header


def test_normalize_zero_gives_zero():
    f_raw = {dim: 0.0 for dim in FEASIBILITY_WEIGHTS}
    l_raw = {dim: 0.0 for dim in LEAD_WEIGHTS}
    f_norm, l_norm = normalize_dimensions(f_raw, l_raw)
    assert all(v == 0 for v in f_norm.values())
    assert all(v == 0 for v in l_norm.values())


def test_normalize_half_scores():
    f_raw = {dim: DIM_RAW_MAX_F.get(dim, 20) / 2 for dim in FEASIBILITY_WEIGHTS}
    l_raw = {dim: DIM_RAW_MAX_L.get(dim, 20) / 2 for dim in LEAD_WEIGHTS}
    f_norm, l_norm = normalize_dimensions(f_raw, l_raw)
    for dim, header in FEASIBILITY_WEIGHTS.items():
        assert abs(f_norm[dim] - header / 2) <= 1


def test_normalize_preserves_all_dimensions():
    f_raw = {dim: 5.0 for dim in FEASIBILITY_WEIGHTS}
    l_raw = {dim: 5.0 for dim in LEAD_WEIGHTS}
    f_norm, l_norm = normalize_dimensions(f_raw, l_raw)
    assert set(f_norm.keys()) == set(FEASIBILITY_WEIGHTS.keys())
    assert set(l_norm.keys()) == set(LEAD_WEIGHTS.keys())


# ── 完整管道 ───────────────────────────────────────────────────

def test_build_scoring_input_produces_valid_engine_input():
    slots = _slots(industry="健身器材", product="力量训练设备")
    answers = {"Q2a": ["A"], "Q5": ["A"]}
    si = build_scoring_input(answers, q1_slots=slots)
    result = calculate_scoring(si)
    assert result.feasibility_score >= 0
    assert result.lead_score >= 0
    assert result.tag is not None
    assert result.lead_priority is not None
    assert len(result.dimension_scores) == 14


def test_pipeline_empty_input_survives():
    si = build_scoring_input({})
    result = calculate_scoring(si)
    assert result.feasibility_score == 0
    assert result.lead_score == 0
    assert result.tag == "观察准备型"
    assert result.lead_priority == "P3"


# ── raw_max 一致性 ─────────────────────────────────────────────

def test_raw_max_matches_header_for_aligned_dimensions():
    assert DIM_RAW_MAX_F["enterprise_base"] == FEASIBILITY_WEIGHTS["enterprise_base"]
    assert DIM_RAW_MAX_L["enterprise_base"] == LEAD_WEIGHTS["enterprise_base"]


def test_raw_max_differs_from_header_by_design():
    assert DIM_RAW_MAX_L["overseas_validation"] == 17.0
    assert LEAD_WEIGHTS["overseas_validation"] == 15
    f_norm, l_norm = normalize_dimensions(
        {"overseas_validation": 17.0}, {"overseas_validation": 17.0}
    )
    assert l_norm["overseas_validation"] == 15


def test_raw_max_all_dimensions_have_positive_values():
    for dim in FEASIBILITY_WEIGHTS:
        assert DIM_RAW_MAX_F[dim] > 0
    for dim in LEAD_WEIGHTS:
        assert DIM_RAW_MAX_L[dim] > 0


# ── 元数据修复验证 ─────────────────────────────────────────────

def test_q12_max_lead_score_is_1():
    from app.scoring.questionnaire import ALL_QUESTIONS
    q12 = next(q for q in ALL_QUESTIONS if q.id == "Q12")
    assert q12.max_lead_score == 1


def test_q13_max_lead_score_is_2():
    from app.scoring.questionnaire import ALL_QUESTIONS
    q13 = next(q for q in ALL_QUESTIONS if q.id == "Q13")
    assert q13.max_lead_score == 2


def test_q14_max_feasibility_score_is_2():
    from app.scoring.questionnaire import ALL_QUESTIONS
    q14 = next(q for q in ALL_QUESTIONS if q.id == "Q14")
    assert q14.max_feasibility_score == 2
