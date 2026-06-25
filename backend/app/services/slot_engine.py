from app.schemas.slots import CompanySlots, SlotMergeResult, SlotValue

_REQUIRED_SLOTS: list[str] = [
    "industry",
    "main_product",
    "overseas_experience",
    "target_market",
    "monthly_budget",
    "consultation_intent",
]

_VALID_FIELDS: set[str] = set(CompanySlots.model_fields.keys())


def normalize_slot_value(field_name: str, slot: SlotValue) -> SlotValue:
    if slot.confidence < 0.0 or slot.confidence > 1.0:
        raise ValueError(
            f"字段 {field_name} 的 confidence 必须在 [0, 1]，实际为 {slot.confidence}"
        )

    value = slot.value
    if isinstance(value, str):
        stripped = value.strip()
        return SlotValue(
            value=stripped if stripped else None,
            confidence=slot.confidence,
            source=slot.source,
        )
    if isinstance(value, list):
        cleaned = list(dict.fromkeys(
            str(v).strip() for v in value if str(v).strip()
        ))
        return SlotValue(
            value=cleaned if cleaned else None,
            confidence=slot.confidence,
            source=slot.source,
        )
    return slot


def merge_slots(
    current: CompanySlots,
    incoming: dict[str, SlotValue],
    min_confidence: float = 0.6,
) -> SlotMergeResult:
    updated: list[str] = []
    low_conf: list[str] = []
    ignored: list[str] = []

    merged_data = {}
    for field in _VALID_FIELDS:
        merged_data[field] = getattr(current, field)

    for field, slot in incoming.items():
        if field not in _VALID_FIELDS:
            ignored.append(field)
            continue

        normalized = normalize_slot_value(field, slot)

        if normalized.value is None:
            ignored.append(field)
            continue

        if normalized.confidence < min_confidence:
            low_conf.append(field)
            continue

        existing = getattr(current, field)
        if existing is None:
            merged_data[field] = normalized
            updated.append(field)
        elif normalized.confidence >= existing.confidence:
            merged_data[field] = normalized
            updated.append(field)
        else:
            ignored.append(field)

    return SlotMergeResult(
        slots=CompanySlots(**merged_data),
        updated_fields=updated,
        low_confidence_fields=low_conf,
        ignored_fields=ignored,
    )


def get_missing_required_slots(slots: CompanySlots) -> list[str]:
    missing = []
    for field in _REQUIRED_SLOTS:
        slot = getattr(slots, field)
        if slot is None or slot.value is None:
            missing.append(field)
    return missing
