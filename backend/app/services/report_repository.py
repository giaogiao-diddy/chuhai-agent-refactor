# TODO: OAuth 后按 current_user 过滤
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Assessment
from app.models.report import UserReport as UserReportModel
from app.schemas.report import UserReport as UserReportSchema
from app.schemas.report_history import ReportDetailResponse, ReportListItem


async def list_user_reports(
    db: AsyncSession, limit: int = 20
) -> list[ReportListItem]:
    query = (
        select(Assessment, UserReportModel)
        .join(UserReportModel, UserReportModel.assessment_id == Assessment.id)
        .order_by(Assessment.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()

    items: list[ReportListItem] = []
    for assessment, user_report_model in rows:
        validated = UserReportSchema.model_validate(user_report_model.report_json)
        items.append(ReportListItem(
            assessment_id=assessment.id,
            status=assessment.status,
            branch=assessment.branch,
            tag=validated.tag,
            feasibility_score=validated.feasibility_score,
            display_score=validated.display_score,
            used_template_report=assessment.used_template_report,
            created_at=assessment.created_at,
            completed_at=assessment.completed_at,
        ))
    return items


async def get_user_report_detail(
    db: AsyncSession, assessment_id: UUID
) -> ReportDetailResponse | None:
    query = (
        select(Assessment, UserReportModel)
        .join(UserReportModel, UserReportModel.assessment_id == Assessment.id)
        .where(Assessment.id == assessment_id)
    )
    result = await db.execute(query)
    row = result.one_or_none()
    if row is None:
        return None

    assessment, user_report_model = row
    validated = UserReportSchema.model_validate(user_report_model.report_json)
    return ReportDetailResponse(
        assessment_id=assessment.id,
        status=assessment.status,
        branch=assessment.branch,
        used_template_report=assessment.used_template_report,
        created_at=assessment.created_at,
        completed_at=assessment.completed_at,
        user_report=validated,
    )
