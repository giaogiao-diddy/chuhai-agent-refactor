from __future__ import annotations
"""评分规则 + 标签生成 — 纯函数模块，无副作用、无 I/O、无外部依赖"""


def calculate_total(answers: list[dict]) -> int:
    """对 17 道计分题求和。Q1 行业输入 score=0，不参与计分。"""
    return sum(a.get("score", 0) for a in answers if a.get("score", 0) > 0)


def score_to_tag(raw_score: int) -> tuple[str, str]:
    """根据 V2 原始总分（17-68）返回标签和解释文本。

    映射公式：display = raw + 43

    原始分 → 展示分 → 标签：
      17-30 → 60-73  → 观察准备型
      31-43 → 74-86  → 轻量试探型
      44-56 → 87-99  → 基础具备型
      57-68 → 100-111 → 优先布局型
    """
    if raw_score <= 30:
        return ("观察准备型", "出海基础尚浅，建议先从定位梳理和轻量内容测试开始。")
    elif raw_score <= 43:
        return ("轻量试探型", "已具备部分条件，可启动强成交人设内容矩阵进行低成本验证。")
    elif raw_score <= 56:
        return ("基础具备型", "基础条件较好，适合系统化推进短视频出海获客体系。")
    else:
        return ("优先布局型", "整体条件成熟，可进行多语种矩阵布局和规模化获客。")


def calculate_score_and_tag(answers: list[dict]) -> dict:
    """一次性返回原始分、展示分、标签和标签解释。"""
    raw_score = calculate_total(answers)
    tag, tag_explanation = score_to_tag(raw_score)
    return {
        "raw_score": raw_score,
        "display_score": raw_score + 43,
        "tag": tag,
        "tag_explanation": tag_explanation,
    }
