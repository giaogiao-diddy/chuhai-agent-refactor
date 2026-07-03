from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.report import UserReport


class PublicReportSummary(BaseModel):
    """留资前可见的报告摘要字段。"""
    feasibility_score: int
    display_score: int
    tag: str
    tag_explanation: str
    preliminary_judgment: str
    strengths: list[str]
    risks: list[str]
    unlock_hint: str


class ReportListItem(BaseModel):
    assessment_id: UUID
    status: str
    branch: str | None = None
    tag: str | None = None
    feasibility_score: int | None = None
    display_score: int | None = None
    used_template_report: bool = False
    created_at: datetime
    completed_at: datetime | None = None
    followup_status: str | None = None
    provider_id: str | None = None
    model_name: str | None = None


class ReportDetailResponse(BaseModel):
    assessment_id: UUID
    status: str
    branch: str | None = None
    used_template_report: bool = False
    created_at: datetime
    completed_at: datetime | None = None
    is_unlocked: bool = False
    report_summary: PublicReportSummary
    user_report: UserReport | None = None
    wechat_qr_url: str | None = None
    followup_status: str | None = None
    provider_id: str | None = None
    model_name: str | None = None
