from __future__ import annotations
"""AI 报告生成 + 模板兜底服务"""

import json


def parse_ai_response(data: dict | str | None) -> dict | None:
    """解析 AI 返回的响应，统一为 dict 或 None。

    Args:
        data: AI 响应 — dict（已解析）、JSON 字符串、或 None

    Returns:
        dict 或 None（解析失败时）
    """
    if data is None:
        return None
    if isinstance(data, dict):
        return data
    if isinstance(data, str) and data.strip():
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def validate_report_fields(data: dict) -> bool:
    """校验 AI 报告 JSON 的字段完整性。

    必须包含 summary_report 和 full_report 两个顶层 key，
    且各自的必填字段非空、类型正确。

    Args:
        data: parse_ai_response 返回的 dict

    Returns:
        True 表示字段完整，False 表示缺失或类型错误
    """
    if not isinstance(data, dict):
        return False

    # 顶层必须有两个 key
    if "summary_report" not in data or "full_report" not in data:
        return False

    summary = data["summary_report"]
    full = data["full_report"]

    if not isinstance(summary, dict) or not isinstance(full, dict):
        return False

    # 部分报告必填字段校验
    if "preliminary_judgment" not in summary:
        return False
    if "strengths" not in summary or not isinstance(summary["strengths"], list):
        return False
    if "risks" not in summary or not isinstance(summary["risks"], list):
        return False

    # 完整报告必填字段校验
    if "summary_conclusion" not in full:
        return False
    if "dimension_scores" not in full or not isinstance(full["dimension_scores"], dict):
        return False
    if "action_plan_30days" not in full or not isinstance(full["action_plan_30days"], list):
        return False

    return True


async def generate_report(assessment_id: int, answers: list[dict], total_score: int, tag: str) -> dict:
    """生成测评报告 — 先调 AI，失败则切模板兜底"""
    # TODO: 构造 Prompt → 调 DeepSeek → JSON 校验 → 写入 DB
    # 失败路径: 调 template_report.build_summary / build_full
    raise NotImplementedError
