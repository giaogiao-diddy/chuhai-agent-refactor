import json
from pathlib import Path

import pytest

from app.scoring import calculate_scoring
from app.schemas.scoring import ScoringInput

FIXTURES = Path(__file__).parent.parent / "fixtures" / "scoring_cases.json"


def _load(name: str) -> dict:
    with open(FIXTURES, encoding="utf-8") as f:
        return json.load(f)[name]


# ── 主流程 ────────────────────────────────────────────────────

def test_calculate_score_returns_priority_layout_tag():
    case = _load("high_scorer")
    result = calculate_scoring(ScoringInput(**case))

    assert result.tag == "优先布局型"
    assert result.lead_priority == "P0"
    assert result.feasibility_score == 89
    assert result.lead_score == 87


def test_calculate_score_returns_observe_tag():
    case = _load("low_scorer")
    result = calculate_scoring(ScoringInput(**case))

    assert result.tag == "观察准备型"
    assert result.lead_priority == "P3"


# ── 标签边界值 ────────────────────────────────────────────────

def test_tag_boundary_25_is_observe():
    result = calculate_scoring(ScoringInput(**_load("tag_boundary_25")))
    assert result.tag == "观察准备型"


def test_tag_boundary_26_is_light():
    result = calculate_scoring(ScoringInput(**_load("tag_boundary_26")))
    assert result.tag == "轻量试探型"


def test_tag_boundary_45_is_light():
    result = calculate_scoring(ScoringInput(**_load("tag_boundary_45")))
    assert result.tag == "轻量试探型"


def test_tag_boundary_46_is_basic():
    result = calculate_scoring(ScoringInput(**_load("tag_boundary_46")))
    assert result.tag == "基础具备型"


def test_tag_boundary_65_is_basic():
    result = calculate_scoring(ScoringInput(**_load("tag_boundary_65")))
    assert result.tag == "基础具备型"


def test_tag_boundary_66_is_priority():
    result = calculate_scoring(ScoringInput(**_load("tag_boundary_66")))
    assert result.tag == "优先布局型"


# ── 校验 ──────────────────────────────────────────────────────

def test_calculate_score_rejects_missing_dimension():
    case = _load("missing_dimension")
    with pytest.raises(ValueError):
        calculate_scoring(ScoringInput(**case))


def test_calculate_score_rejects_out_of_range():
    with pytest.raises(ValueError):
        calculate_scoring(ScoringInput(
            feasibility_dimensions={d: 10 for d in ["enterprise_base","overseas_validation","product_supply_chain","path_clarity","content_fitness","conversion_readiness","action_readiness"]},
            lead_dimensions={"enterprise_base": 150, "overseas_validation": 0, "product_supply_chain": 0, "path_clarity": 0, "content_fitness": 0, "conversion_readiness": 0, "action_readiness": 0},
        ))


def test_calculate_score_rejects_unknown_feasibility_dimension():
    case = _load("unknown_feasibility_dimension")
    with pytest.raises(ValueError):
        calculate_scoring(ScoringInput(**case))


def test_calculate_score_rejects_unknown_lead_dimension():
    case = _load("unknown_lead_dimension")
    with pytest.raises(ValueError):
        calculate_scoring(ScoringInput(**case))


# ── display_score ──────────────────────────────────────────────

def test_display_score_equals_feasibility_score():
    case = _load("high_scorer")
    result = calculate_scoring(ScoringInput(**case))
    assert result.display_score == result.feasibility_score


# ── normalized_score ───────────────────────────────────────────

def test_normalized_score_is_0_to_100():
    result = calculate_scoring(ScoringInput(**_load("high_scorer")))
    for ds in result.dimension_scores:
        assert 0 <= ds.normalized_score <= 100


# ── lead_priority 边界值 ───────────────────────────────────────

def test_lead_boundary_20_is_p3():
    result = calculate_scoring(ScoringInput(**_load("lead_boundary_20")))
    assert result.lead_priority == "P3"


def test_lead_boundary_21_is_p2():
    result = calculate_scoring(ScoringInput(**_load("lead_boundary_21")))
    assert result.lead_priority == "P2"


def test_lead_boundary_40_is_p2():
    result = calculate_scoring(ScoringInput(**_load("lead_boundary_40")))
    assert result.lead_priority == "P2"


def test_lead_boundary_41_is_p1():
    result = calculate_scoring(ScoringInput(**_load("lead_boundary_41")))
    assert result.lead_priority == "P1"


def test_lead_boundary_60_is_p1():
    result = calculate_scoring(ScoringInput(**_load("lead_boundary_60")))
    assert result.lead_priority == "P1"


def test_lead_boundary_61_is_p0():
    result = calculate_scoring(ScoringInput(**_load("lead_boundary_61")))
    assert result.lead_priority == "P0"
