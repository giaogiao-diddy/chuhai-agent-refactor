from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.report import LeadReport, UserReport

FollowupStatus = Literal["未联系", "已联系", "已预约", "已成交"]


class AdminLeadFollowupUpdate(BaseModel):
    followup_status: FollowupStatus
    followup_note: str | None = Field(default=None, max_length=500)


class AdminLeadListItem(BaseModel):
    submission_id: str
    assessment_id: str
    contact_name: str
    phone: str
    wechat_id: str | None = None
    company_name: str | None = None
    created_at: datetime
    tag: str | None = None
    feasibility_score: int | None = None
    display_score: int | None = None
    lead_priority: str | None = None
    used_template_report: bool = False
    report_completed_at: datetime | None = None
    followup_status: FollowupStatus = "未联系"


class AdminLeadDetail(BaseModel):
    submission_id: str
    assessment_id: str
    contact_name: str
    phone: str
    wechat_id: str | None = None
    company_name: str | None = None
    note: str | None = None
    created_at: datetime
    tag: str | None = None
    feasibility_score: int | None = None
    display_score: int | None = None
    lead_priority: str | None = None
    used_template_report: bool = False
    report_completed_at: datetime | None = None
    followup_status: FollowupStatus = "未联系"
    followup_note: str | None = None
    user_report: UserReport
    lead_report: LeadReport
