"""engine.py — 评分引擎：接收归一化后的 7 维 F/L 分，计算标签/优先级/维度展示。

输入合同：ScoringInput.feasibility_dimensions 和 lead_dimensions 必须是
已经过 answer_scoring.py 归一化的维度分，每个维度值在 [0, header_weight] 范围内。
engine 不做逐题计分，只做：维度校验 → 总分求和 → 标签查表 → 雷达图构建。

归一化规则见 answer_scoring.py 和 docs/scoring-consistency-audit.md。
"""

from app.schemas.scoring import DimensionScore, ScoringInput, ScoringResult
from app.scoring.rules import (
    FEASIBILITY_WEIGHTS,
    LEAD_WEIGHTS,
    TAG_EXPLANATIONS,
    TAG_THRESHOLDS,
    LEAD_PRIORITY_THRESHOLDS,
)


def _validate_dimensions(input_data: ScoringInput) -> None:
    f_dims = input_data.feasibility_dimensions
    l_dims = input_data.lead_dimensions

    if set(f_dims) != set(FEASIBILITY_WEIGHTS):
        extra_f = set(f_dims) - set(FEASIBILITY_WEIGHTS)
        missing_f = set(FEASIBILITY_WEIGHTS) - set(f_dims)
        msg = ""
        if extra_f:
            msg += f"未知 feasibility 维度: {extra_f}. "
        if missing_f:
            msg += f"缺少 feasibility 维度: {missing_f}. "
        raise ValueError(msg.strip())

    if set(l_dims) != set(LEAD_WEIGHTS):
        extra_l = set(l_dims) - set(LEAD_WEIGHTS)
        missing_l = set(LEAD_WEIGHTS) - set(l_dims)
        msg = ""
        if extra_l:
            msg += f"未知 lead 维度: {extra_l}. "
        if missing_l:
            msg += f"缺少 lead 维度: {missing_l}. "
        raise ValueError(msg.strip())

    for dim, score in f_dims.items():
        max_score = FEASIBILITY_WEIGHTS[dim]
        if not (0 <= score <= max_score):
            raise ValueError(f"feasibility 维度 {dim} 分数 {score} 超出范围 [0, {max_score}]")

    for dim, score in l_dims.items():
        max_score = LEAD_WEIGHTS[dim]
        if not (0 <= score <= max_score):
            raise ValueError(f"lead 维度 {dim} 分数 {score} 超出范围 [0, {max_score}]")


def _sum_dimensions(dimensions: dict[str, int]) -> int:
    return sum(dimensions.values())


def _lookup_label(total: int, thresholds: list[tuple[int, int, str]]) -> str:
    for lo, hi, label in thresholds:
        if lo <= total <= hi:
            return label
    return thresholds[-1][2]


def _normalize(raw: int, max_val: int) -> int:
    if max_val <= 0:
        raise ValueError(f"max_score 必须 > 0，实际为 {max_val}")
    return round(raw / max_val * 100)


def _build_dimension_scores(
    f_dims: dict[str, int], l_dims: dict[str, int]
) -> list[DimensionScore]:
    results: list[DimensionScore] = []
    for dim in FEASIBILITY_WEIGHTS:
        max_score = FEASIBILITY_WEIGHTS[dim]
        results.append(
            DimensionScore(
                name=f"{dim}_feasibility",
                raw_score=f_dims[dim],
                max_score=max_score,
                normalized_score=_normalize(f_dims[dim], max_score),
            )
        )
    for dim in LEAD_WEIGHTS:
        max_score = LEAD_WEIGHTS[dim]
        results.append(
            DimensionScore(
                name=f"{dim}_lead",
                raw_score=l_dims[dim],
                max_score=max_score,
                normalized_score=_normalize(l_dims[dim], max_score),
            )
        )
    return results


def _derive_strengths(f_total: int) -> list[str]:
    if f_total >= 46:
        return [
            "企业基本盘扎实，具备规模化出海潜力",
            "产品与供应链能力较强，对海外客户具有吸引力",
        ]
    if f_total >= 26:
        return [
            "企业已具备部分出海条件，可在单一市场先行测试",
        ]
    return [
        "企业已开始评估出海路径，迈出了第一步",
    ]


def _derive_risks(f_total: int) -> list[str]:
    common = "海外目标市场存在不确定性，建议持续关注政策与竞争动态"
    if f_total < 26:
        return [common, "产品、供应链或团队基础尚不完整，建议先补齐核心能力"]
    if f_total < 46:
        return [common, "单一市场验证存在集中风险，建议增加备选市场方案"]
    return [common, "进入成熟市场时注意合规与品牌信任门槛"]


def calculate_scoring(input_data: ScoringInput) -> ScoringResult:
    _validate_dimensions(input_data)

    f_total = _sum_dimensions(input_data.feasibility_dimensions)
    l_total = _sum_dimensions(input_data.lead_dimensions)

    tag = _lookup_label(f_total, TAG_THRESHOLDS)
    lead_priority = _lookup_label(l_total, LEAD_PRIORITY_THRESHOLDS)

    return ScoringResult(
        feasibility_score=f_total,
        lead_score=l_total,
        display_score=f_total,
        tag=tag,
        tag_explanation=TAG_EXPLANATIONS[tag],
        preliminary_judgment=f"该企业出海可行性评分为 {f_total}/100，属于「{tag}」。",
        dimension_scores=_build_dimension_scores(
            input_data.feasibility_dimensions, input_data.lead_dimensions
        ),
        strengths=_derive_strengths(f_total),
        risks=_derive_risks(f_total),
        lead_priority=lead_priority,
    )
