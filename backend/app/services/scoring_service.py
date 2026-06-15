from __future__ import annotations
"""评分规则 + 标签生成 — 纯函数模块，无副作用、无 I/O、无外部依赖"""


def calculate_total(answers: list[dict]) -> int:
    """对每题分数求和。每题 1-4 分，共 15 题，原始分范围 15-60。"""
    return sum(a["score"] for a in answers)


def score_to_tag(raw_score: int) -> tuple[str, str]:
    """根据原始总分（15-60）返回标签和解释文本。

    映射公式：display = raw + 45

    原始分 → 展示分 → 标签：
      15-25 → 60-70  → 观察准备型
      26-35 → 71-80  → 轻量试探型
      36-45 → 81-90  → 基础具备型
      46-60 → 91-100 → 优先布局型
    """
    if raw_score <= 25:
        return ("观察准备型", "当前仍处于准备阶段，适合先完成调研、产品梳理和低成本验证。")
    elif raw_score <= 35:
        return ("轻量试探型", "已具备部分条件，但关键能力尚未完整，适合小预算、轻渠道测试。")
    elif raw_score <= 45:
        return ("基础具备型", "具备一定出海基础，可以进入系统化测试阶段。")
    else:
        return ("优先布局型", "整体条件较成熟，具备较高海外市场开拓潜力。")
