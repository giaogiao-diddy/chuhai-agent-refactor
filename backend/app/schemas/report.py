from __future__ import annotations
"""报告相关模型"""

from pydantic import BaseModel


class SummaryReport(BaseModel):
    """部分报告结构"""
    total_score: int
    display_score: int
    tag: str
    tag_explanation: str
    preliminary_judgment: str
    positioning_assessment: str
    content_assessment: str
    conversion_assessment: str
    strengths: list[str]
    risks: list[str]
    unlock_hint: str


class FullReport(BaseModel):
    """完整报告结构"""
    summary_conclusion: str
    positioning_assessment: str
    content_assessment: str
    conversion_assessment: str
    dimension_scores: dict
    recommended_path: str
    risk_reminder: str
    action_plan_30days: list[str]
    consultant_guide: str


class AIReportOutput(BaseModel):
    """AI 返回的严格 JSON 结构"""
    summary_report: dict
    full_report: dict


class MyReportResponse(BaseModel):
    """我的报告 — 报告卡片"""
    assessment_id: int
    total_score: int
    tag: str
    display_score: int
    completed_at: str | None = None
    summary: dict | None = None
