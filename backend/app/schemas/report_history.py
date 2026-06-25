from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.report import UserReport


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


class ReportDetailResponse(BaseModel):
    assessment_id: UUID
    status: str
    branch: str | None = None
    used_template_report: bool = False
    created_at: datetime
    completed_at: datetime | None = None
    user_report: UserReport
