import json
from pathlib import Path

from app.scoring.rules import FEASIBILITY_WEIGHTS, LEAD_WEIGHTS
from app.schemas.slots import CompanySlots, SlotValue
from app.services.slot_to_score import build_scoring_input_from_slots

FIXTURES = Path(__file__).parent.parent / "fixtures" / "slot_to_score_cases.json"


def _load_slots(name: str) -> CompanySlots:
    with open(FIXTURES, encoding="utf-8") as f:
        data = json.load(f)[name]
    built = {}
    for key, val in data.items():
        built[key] = SlotValue(**val) if val is not None else None
    return CompanySlots(**built)


# ── 维度完整性 ──────────────────────────────────────────────────

def test_build_scoring_input_outputs_all_dimensions():
    slots = _load_slots("full_slots")
    result = build_scoring_input_from_slots(slots)

    assert set(result.feasibility_dimensions) == set(FEASIBILITY_WEIGHTS)
    assert set(result.lead_dimensions) == set(LEAD_WEIGHTS)


# ── 上限 ───────────────────────────────────────────────────────

def test_build_scoring_input_caps_scores():
    slots = _load_slots("full_slots")
    result = build_scoring_input_from_slots(slots)

    for dim, score in result.feasibility_dimensions.items():
        assert score <= FEASIBILITY_WEIGHTS[dim]
    for dim, score in result.lead_dimensions.items():
        assert score <= LEAD_WEIGHTS[dim]


# ── 空输入 ─────────────────────────────────────────────────────

def test_build_scoring_input_missing_slots_returns_zeroes():
    slots = _load_slots("empty_slots")
    result = build_scoring_input_from_slots(slots)

    assert all(v == 0 for v in result.feasibility_dimensions.values())
    assert all(v == 0 for v in result.lead_dimensions.values())


# ── 海外经验 ───────────────────────────────────────────────────

def test_build_scoring_input_overseas_experience_positive():
    slots = _load_slots("overseas_positive")
    result = build_scoring_input_from_slots(slots)

    assert result.feasibility_dimensions["overseas_validation"] > 0
    assert result.lead_dimensions["overseas_validation"] > 0


def test_build_scoring_input_overseas_experience_negative():
    slots = _load_slots("overseas_negative")
    result = build_scoring_input_from_slots(slots)

    assert result.feasibility_dimensions["overseas_validation"] == 0
    assert result.lead_dimensions["overseas_validation"] == 0


# ── 咨询意向 ───────────────────────────────────────────────────

def test_build_scoring_input_strong_consultation_intent():
    slots = _load_slots("strong_intent")
    result = build_scoring_input_from_slots(slots)

    assert result.feasibility_dimensions["action_readiness"] == 5
    assert result.lead_dimensions["action_readiness"] == 15


# ── 打分流水线 ─────────────────────────────────────────────────

def test_build_scoring_input_can_be_scored():
    from app.scoring import calculate_scoring

    slots = _load_slots("full_slots")
    scoring_input = build_scoring_input_from_slots(slots)
    scoring_result = calculate_scoring(scoring_input)

    assert scoring_result.tag is not None
    assert scoring_result.lead_priority is not None
