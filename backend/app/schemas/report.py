from pydantic import BaseModel, Field

from app.schemas.scoring import DimensionScore


class RawAIReport(BaseModel):
    summary_conclusion: str
    positioning_assessment: str
    content_assessment: str
    conversion_assessment: str
    recommended_path: str
    risk_reminder: str
    action_plan_30days: list[str] = Field(min_length=4, max_length=4)
    consultant_guide: str
    sales_followup: str
    consultant_notes: str


class UserReport(BaseModel):
    feasibility_score: int
    display_score: int
    tag: str
    tag_explanation: str
    preliminary_judgment: str
    strengths: list[str]
    risks: list[str]
    summary_conclusion: str
    positioning_assessment: str
    content_assessment: str
    conversion_assessment: str
    dimension_scores: list[DimensionScore]
    recommended_path: str
    risk_reminder: str
    action_plan_30days: list[str] = Field(min_length=4, max_length=4)
    consultant_guide: str
    unlock_hint: str = "添加企业微信顾问解锁完整报告和1v1深度解读"


class LeadReport(BaseModel):
    lead_score: int
    lead_priority: str
    tag: str
    company_name: str | None = None
    industry: str | None = None
    product: str | None = None
    target_market: str | None = None
    summary_conclusion: str = ""
    sales_followup: str
    consultant_notes: str
    recommended_next_action: str = ""


class ReportBundle(BaseModel):
    raw_report: RawAIReport
    user_report: UserReport
    lead_report: LeadReport
