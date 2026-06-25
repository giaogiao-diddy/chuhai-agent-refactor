# 7 维度权重 — 严格对齐 docs/scoring-design.md
FEASIBILITY_WEIGHTS: dict[str, int] = {
    "enterprise_base": 20,
    "overseas_validation": 20,
    "product_supply_chain": 15,
    "path_clarity": 10,
    "content_fitness": 20,
    "conversion_readiness": 10,
    "action_readiness": 5,
}

LEAD_WEIGHTS: dict[str, int] = {
    "enterprise_base": 20,
    "overseas_validation": 15,
    "product_supply_chain": 12,
    "path_clarity": 8,
    "content_fitness": 15,
    "conversion_readiness": 15,
    "action_readiness": 15,
}

# 可行性标签 — feasibility_score (0-100)
TAG_OBSERVE = "观察准备型"
TAG_LIGHT = "轻量试探型"
TAG_BASIC = "基础具备型"
TAG_PRIORITY = "优先布局型"

TAG_THRESHOLDS: list[tuple[int, int, str]] = [
    (0, 25, TAG_OBSERVE),
    (26, 45, TAG_LIGHT),
    (46, 65, TAG_BASIC),
    (66, 100, TAG_PRIORITY),
]

# 顾问跟进优先级 — lead_score (0-100)
PRIORITY_P0 = "P0"
PRIORITY_P1 = "P1"
PRIORITY_P2 = "P2"
PRIORITY_P3 = "P3"

LEAD_PRIORITY_THRESHOLDS: list[tuple[int, int, str]] = [
    (61, 100, PRIORITY_P0),
    (41, 60, PRIORITY_P1),
    (21, 40, PRIORITY_P2),
    (0, 20, PRIORITY_P3),
]

TAG_EXPLANATIONS: dict[str, str] = {
    TAG_OBSERVE: "企业出海基础较为薄弱，建议先完成行业调研、产品定位和团队组建等基础准备。",
    TAG_LIGHT: "企业具备初步出海条件，建议选择单一低风险市场进行小成本测试验证。",
    TAG_BASIC: "企业出海条件较完善，建议优先夯实目标市场适配度并制定客户转化路径。",
    TAG_PRIORITY: "企业出海条件成熟，产品、供应链、团队与预算均具备竞争力，建议立即启动。",
}
