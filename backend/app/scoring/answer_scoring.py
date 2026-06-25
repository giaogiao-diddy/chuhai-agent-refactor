# answer_scoring.py — 逐题答案 → 维度原始分 → 归一化 → ScoringInput
# 输入：{question_id: [option_ids]}，输出：engine 可直接使用的 ScoringInput
# 归一化规则：每维度独立 raw/raw_max*header_weight，不做跨维度补偿

from app.scoring.questionnaire import ALL_QUESTIONS, Q1
from app.scoring.rules import FEASIBILITY_WEIGHTS, LEAD_WEIGHTS
from app.schemas.scoring import ScoringInput
from app.schemas.slots import CompanySlots


def _compute_dimension_raw_max() -> tuple[dict[str, float], dict[str, float]]:
    f_max: dict[str, float] = {}
    l_max: dict[str, float] = {}
    for q in ALL_QUESTIONS:
        if not q.is_scored:
            continue
        dim = q.dimension
        f_max[dim] = f_max.get(dim, 0.0) + q.max_feasibility_score
        l_max[dim] = l_max.get(dim, 0.0) + q.max_lead_score
    return f_max, l_max


DIM_RAW_MAX_F: dict[str, float]
DIM_RAW_MAX_L: dict[str, float]
DIM_RAW_MAX_F, DIM_RAW_MAX_L = _compute_dimension_raw_max()


def score_q1_information_completeness(
    slots: CompanySlots,
) -> tuple[float, float]:
    has_industry = (
        slots.industry is not None
        and slots.industry.value is not None
        and str(slots.industry.value).strip() != ""
    )
    has_product = (
        slots.main_product is not None
        and slots.main_product.value is not None
        and str(slots.main_product.value).strip() != ""
    )
    if has_industry and has_product:
        return (2.0, 3.0)
    elif has_industry or has_product:
        return (1.0, 1.0)
    else:
        return (0.0, 0.0)


EXPERIENCED_QUESTION_IDS = {q.id for q in ALL_QUESTIONS if q.branch == "experienced"}


def score_answers(
    answers: dict[str, list[str]],
    branch: str = "experienced",
    q1_slots: CompanySlots | None = None,
) -> tuple[dict[str, float], dict[str, float]]:
    f_raw: dict[str, float] = {dim: 0.0 for dim in FEASIBILITY_WEIGHTS}
    l_raw: dict[str, float] = {dim: 0.0 for dim in LEAD_WEIGHTS}

    if q1_slots is not None:
        f_q1, l_q1 = score_q1_information_completeness(q1_slots)
        f_raw[Q1.dimension] += f_q1
        l_raw[Q1.dimension] += l_q1

    q_map: dict[str, object] = {q.id: q for q in ALL_QUESTIONS}

    for q_id, selected in answers.items():
        q = q_map.get(q_id)
        if q is None:
            raise ValueError(f"未知题号: {q_id}")
        if not q.is_scored:
            continue
        if q.kind == "open_text":
            continue

        if branch == "inexperienced" and q.branch == "experienced":
            raise ValueError(
                f"inexperienced 分支不允许 experienced 题目: {q_id}"
            )

        valid_ids = {o.id for o in q.options}
        invalid = [s for s in selected if s not in valid_ids]
        if invalid:
            raise ValueError(f"{q_id} 的无效选项: {invalid}，有效选项: {valid_ids}")

        if q.kind == "single_choice":
            if len(selected) != 1:
                raise ValueError(
                    f"{q_id} 是单选题，期望 1 个选项，实际 {len(selected)} 个: {selected}"
                )
            opt = next(o for o in q.options if o.id == selected[0])
            f_raw[q.dimension] += opt.feasibility_score
            l_raw[q.dimension] += opt.lead_score

        elif q.kind == "multiple_choice":
            f_sum = sum(o.feasibility_score for o in q.options if o.id in selected)
            l_sum = sum(o.lead_score for o in q.options if o.id in selected)
            f_raw[q.dimension] += min(f_sum, q.max_feasibility_score)
            l_raw[q.dimension] += min(l_sum, q.max_lead_score)

    return f_raw, l_raw


def normalize_dimensions(
    f_raw: dict[str, float],
    l_raw: dict[str, float],
) -> tuple[dict[str, int], dict[str, int]]:
    f_norm: dict[str, int] = {}
    l_norm: dict[str, int] = {}

    for dim, header_weight in FEASIBILITY_WEIGHTS.items():
        raw = f_raw.get(dim, 0.0)
        raw_max = DIM_RAW_MAX_F.get(dim, header_weight)
        f_norm[dim] = round(raw / raw_max * header_weight) if raw_max > 0 else 0

    for dim, header_weight in LEAD_WEIGHTS.items():
        raw = l_raw.get(dim, 0.0)
        raw_max = DIM_RAW_MAX_L.get(dim, header_weight)
        l_norm[dim] = round(raw / raw_max * header_weight) if raw_max > 0 else 0

    return f_norm, l_norm


def build_scoring_input(
    answers: dict[str, list[str]],
    branch: str = "experienced",
    q1_slots: CompanySlots | None = None,
    company_name: str | None = None,
    industry: str | None = None,
    product: str | None = None,
    target_market: str | None = None,
) -> ScoringInput:
    f_raw, l_raw = score_answers(answers, branch, q1_slots)
    f_norm, l_norm = normalize_dimensions(f_raw, l_raw)
    return ScoringInput(
        company_name=company_name,
        industry=industry,
        product=product,
        target_market=target_market,
        feasibility_dimensions=f_norm,
        lead_dimensions=l_norm,
    )
