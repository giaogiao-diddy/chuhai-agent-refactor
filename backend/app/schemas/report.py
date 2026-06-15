from __future__ import annotations
"""报告相关模型"""

from pydantic import BaseModel


class SummaryReport(BaseModel):
    """部分报告结构"""
    total_score: int
    tag: str
    tag_explanation: str
    preliminary_judgment: str
    strengths: list[str]
    risks: list[str]
    unlock_hint: str


class FullReport(BaseModel):
    """完整报告结构"""
    summary_conclusion: str
    dimension_scores: dict[str, int]
    recommended_path: str
    risk_reminder: str
    action_plan_30days: list[str]
    consultant_guide: str


class AIReportOutput(BaseModel):
    """AI 返回的严格 JSON 结构"""
    summary_report: dict
    full_report: dict
