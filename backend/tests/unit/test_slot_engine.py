import json
from pathlib import Path

import pytest

from app.schemas.slots import CompanySlots, SlotValue
from app.services.slot_engine import (
    get_missing_required_slots,
    merge_slots,
    normalize_slot_value,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "slot_cases.json"


def _load(name: str) -> dict:
    with open(FIXTURES, encoding="utf-8") as f:
        return json.load(f)[name]


def _make_slots(data: dict) -> CompanySlots:
    built = {}
    for key, val in data.items():
        if val is None:
            built[key] = None
        else:
            built[key] = SlotValue(**val)
    return CompanySlots(**built)


# ── normalize_slot_value ───────────────────────────────────────

def test_normalize_slot_value_trims_string():
    result = normalize_slot_value("industry", SlotValue(value="  健身器材  ", confidence=0.9))
    assert result.value == "健身器材"


def test_normalize_slot_value_empty_string_to_none():
    result = normalize_slot_value("industry", SlotValue(value="   ", confidence=0.9))
    assert result.value is None


def test_normalize_slot_value_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        normalize_slot_value("industry", SlotValue(value="x", confidence=1.5))
    with pytest.raises(ValueError):
        normalize_slot_value("industry", SlotValue(value="x", confidence=-0.1))


def test_normalize_slot_value_deduplicates_list():
    result = normalize_slot_value(
        "target_market",
        SlotValue(value=["北美", "", "北美", "东南亚"], confidence=0.9),
    )
    assert result.value == ["北美", "东南亚"]


# ── merge_slots ────────────────────────────────────────────────

def test_merge_slots_updates_empty_current():
    case = _load("empty_current")
    current = _make_slots(case["current"])
    incoming = {k: SlotValue(**v) for k, v in case["incoming"].items()}
    result = merge_slots(current, incoming)

    assert result.slots.industry.value == "健身器材"
    assert "industry" in result.updated_fields
    assert result.ignored_fields == []


def test_merge_slots_rejects_low_confidence_update():
    case = _load("low_confidence")
    current = _make_slots(case["current"])
    incoming = {k: SlotValue(**v) for k, v in case["incoming"].items()}
    result = merge_slots(current, incoming)

    assert result.slots.industry.value == "五金配件"
    assert "industry" in result.low_confidence_fields


def test_merge_slots_overwrites_when_confidence_is_higher():
    case = _load("higher_confidence")
    current = _make_slots(case["current"])
    incoming = {k: SlotValue(**v) for k, v in case["incoming"].items()}
    result = merge_slots(current, incoming)

    assert result.slots.industry.value == "医疗器械"


def test_merge_slots_keeps_existing_when_confidence_is_lower():
    case = _load("lower_confidence")
    current = _make_slots(case["current"])
    incoming = {k: SlotValue(**v) for k, v in case["incoming"].items()}
    result = merge_slots(current, incoming)

    assert result.slots.industry.value == "五金配件"
    assert "industry" in result.low_confidence_fields


def test_merge_slots_ignores_unknown_fields():
    case = _load("unknown_field")
    current = _make_slots(case["current"])
    incoming = {k: SlotValue(**v) for k, v in case["incoming"].items()}
    result = merge_slots(current, incoming)

    assert result.slots.industry.value == "健身器材"
    assert "not_a_valid_field" in result.ignored_fields


# ── get_missing_required_slots ─────────────────────────────────

def test_get_missing_required_slots_returns_missing_fields():
    case = _load("missing_required")
    slots = _make_slots(case["slots"])
    missing = get_missing_required_slots(slots)

    assert "main_product" in missing
    assert "target_market" in missing
    assert "monthly_budget" in missing
    assert "consultation_intent" in missing
    assert "industry" not in missing
    assert "overseas_experience" not in missing


# ── null value 防护 ────────────────────────────────────────────

def test_merge_slots_rejects_null_value_even_with_high_confidence():
    case = _load("null_value_high_confidence")
    current = _make_slots(case["current"])
    incoming = {k: SlotValue(**v) for k, v in case["incoming"].items()}
    result = merge_slots(current, incoming)

    assert result.slots.industry.value == "五金配件"
    assert "industry" in result.ignored_fields


def test_merge_slots_ignores_when_confidence_not_high_enough():
    case = _load("not_high_enough_confidence")
    current = _make_slots(case["current"])
    incoming = {k: SlotValue(**v) for k, v in case["incoming"].items()}
    result = merge_slots(current, incoming)

    assert result.slots.industry.value == "五金配件"
    assert "industry" in result.ignored_fields


def test_merge_slots_rejects_empty_list():
    case = _load("empty_list_incoming")
    current = _make_slots(case["current"])
    incoming = {k: SlotValue(**v) for k, v in case["incoming"].items()}
    result = merge_slots(current, incoming)

    assert result.slots.target_market.value == ["北美", "东南亚"]
    assert "target_market" in result.ignored_fields


def test_get_missing_required_slots_returns_empty_when_all_present():
    case = _load("all_required")
    slots = _make_slots(case["slots"])
    missing = get_missing_required_slots(slots)

    assert missing == []
