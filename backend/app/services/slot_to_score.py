"""slot_to_score.py — MVP 槽位→评分映射器（FALLBACK ONLY）。

⚠️ 此模块仅为 MVP 调试期的临时实时估分方案。
   正式评分必须使用 app.scoring.answer_scoring.build_scoring_input()，
   基于 31 题逐选项分值 + 维度归一化。

   此模块的定位：
   - MVP 调试期：对话中快速估分（不做精确计分）
   - 正式报告生成：禁止使用此模块
   - 后续迭代：考虑删除或全面重构为 questionnaire 驱动

   架构决策见 docs/scoring-consistency-audit.md 和 /grill-with-docs 决议。
"""
from app.schemas.scoring import ScoringInput
from app.schemas.slots import CompanySlots, SlotValue
from app.scoring.rules import FEASIBILITY_WEIGHTS, LEAD_WEIGHTS


def _has_value(slot: SlotValue | None) -> bool:
    return slot is not None and slot.value is not None


def _contains_any(value: str | None, keywords: list[str]) -> bool:
    if not value or not isinstance(value, str):
        return False
    return any(kw in value for kw in keywords)


_OVERSEAS_POSITIVE = [
    "有海外", "有订单", "有客户", "有询盘", "出口", "外贸",
    "海外客户", "海外订单", "海外业务", "占比",
]
_OVERSEAS_NEGATIVE = ["没有", "无", "没做过", "完全没有", "从未"]

_INTENT_STRONG = ["愿意", "预约", "尽快", "想咨询", "想预约", "尽快预约"]
_INTENT_WEAK = ["考虑", "先了解", "了解", "看看", "再说", "不一定"]


def _score_enterprise_base(
    slots: CompanySlots, f: dict[str, int], l: dict[str, int]
) -> None:
    if _has_value(slots.annual_revenue):
        f["enterprise_base"] += 8
        l["enterprise_base"] += 8
    if _has_value(slots.team_size):
        f["enterprise_base"] += 6
        l["enterprise_base"] += 6
    if _has_value(slots.sales_team_size):
        f["enterprise_base"] += 6
        l["enterprise_base"] += 6


def _score_overseas_validation(
    slots: CompanySlots, f: dict[str, int], l: dict[str, int]
) -> None:
    exp_val = slots.overseas_experience.value if _has_value(slots.overseas_experience) else None
    if isinstance(exp_val, str):
        if _contains_any(exp_val, _OVERSEAS_NEGATIVE):
            return  # 无海外经验 → 0 分
        if _contains_any(exp_val, _OVERSEAS_POSITIVE):
            f["overseas_validation"] += 12
            l["overseas_validation"] += 10
    if _has_value(slots.overseas_order_ratio):
        f["overseas_validation"] += 8
        l["overseas_validation"] += 5


def _score_product_supply_chain(
    slots: CompanySlots, f: dict[str, int], l: dict[str, int]
) -> None:
    if _has_value(slots.main_product):
        f["product_supply_chain"] += 5
        l["product_supply_chain"] += 4
    if _has_value(slots.industry):
        f["product_supply_chain"] += 5
        l["product_supply_chain"] += 4
    if _has_value(slots.company_name):
        f["product_supply_chain"] += 3
        l["product_supply_chain"] += 2


def _score_path_clarity(
    slots: CompanySlots, f: dict[str, int], l: dict[str, int]
) -> None:
    if _has_value(slots.target_market):
        f["path_clarity"] += 6
        l["path_clarity"] += 5
    if _has_value(slots.monthly_budget):
        f["path_clarity"] += 4
        l["path_clarity"] += 3


def _score_content_fitness(
    slots: CompanySlots, f: dict[str, int], l: dict[str, int]
) -> None:
    if _has_value(slots.content_capability):
        f["content_fitness"] += 12
        l["content_fitness"] += 8


def _score_conversion_readiness(
    slots: CompanySlots, f: dict[str, int], l: dict[str, int]
) -> None:
    if _has_value(slots.conversion_channel):
        f["conversion_readiness"] += 8
        l["conversion_readiness"] += 10


def _score_action_readiness(
    slots: CompanySlots, f: dict[str, int], l: dict[str, int]
) -> None:
    if not _has_value(slots.consultation_intent):
        return
    val = slots.consultation_intent.value
    if isinstance(val, str) and _contains_any(val, _INTENT_STRONG):
        f["action_readiness"] += 5
        l["action_readiness"] += 15
    elif isinstance(val, str) and _contains_any(val, _INTENT_WEAK):
        f["action_readiness"] += 2
        l["action_readiness"] += 5


_SCORERS = [
    _score_enterprise_base,
    _score_overseas_validation,
    _score_product_supply_chain,
    _score_path_clarity,
    _score_content_fitness,
    _score_conversion_readiness,
    _score_action_readiness,
]


def _cap(dims: dict[str, int], weights: dict[str, int]) -> dict[str, int]:
    return {k: min(dims[k], weights[k]) for k in weights}


def build_scoring_input_from_slots(slots: CompanySlots) -> ScoringInput:
    f = {k: 0 for k in FEASIBILITY_WEIGHTS}
    l = {k: 0 for k in LEAD_WEIGHTS}

    for scorer in _SCORERS:
        scorer(slots, f, l)

    return ScoringInput(
        company_name=slots.company_name.value if _has_value(slots.company_name) else None,
        industry=slots.industry.value if _has_value(slots.industry) else None,
        product=slots.main_product.value if _has_value(slots.main_product) else None,
        target_market=slots.target_market.value if _has_value(slots.target_market) else None,
        feasibility_dimensions=_cap(f, FEASIBILITY_WEIGHTS),
        lead_dimensions=_cap(l, LEAD_WEIGHTS),
    )
