from __future__ import annotations
"""后台管理查询/响应模型"""

from pydantic import BaseModel


class LeadFilter(BaseModel):
    page: int = 1
    size: int = 20
    tag: str | None = None
    is_unlocked: bool | None = None


class LeadDetailResponse(BaseModel):
    id: int
    name: str
    contact: str
    company: str
    role: str
    assessment_id: int
    total_score: int | None = None
    tag: str | None = None
    is_unlocked: bool = False
    created_at: str | None = None

    class Config:
        from_attributes = True


class AssessmentDetailResponse(BaseModel):
    id: int
    user_id: int
    total_score: int | None = None
    tag: str | None = None
    status: str
    answers: list[dict] = []
    report: dict | None = None
    created_at: str | None = None
    completed_at: str | None = None


class AIReportLogResponse(BaseModel):
    id: int
    assessment_id: int
    model: str
    status: str
    error_message: str | None = None
    latency_ms: int | None = None
    created_at: str | None = None

    class Config:
        from_attributes = True


class FollowNoteCreate(BaseModel):
    lead_id: int
    status: str = "uncontacted"
    remark: str = ""


class ShareRecordCreate(BaseModel):
    assessment_id: int
    share_scene: str = "moment"


class ShareRecordResponse(BaseModel):
    reward_minutes: int
    total_benefit_minutes: int
