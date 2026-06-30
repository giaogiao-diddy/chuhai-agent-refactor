# TODO: OAuth 后按 current_user 过滤
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Assessment, LeadSubmission, User
from app.models.report import UserReport as UserReportModel
from app.schemas.report import UserReport as UserReportSchema
from app.schemas.report_history import PublicReportSummary, ReportDetailResponse, ReportListItem


def _wechat_openid_from_anonymous(anonymous_user_id: str) -> str:
    return f"anonymous:{anonymous_user_id}"


def _build_summary(validated: UserReportSchema) -> PublicReportSummary:
    return PublicReportSummary(
        feasibility_score=validated.feasibility_score,
        display_score=validated.display_score,
        tag=validated.tag,
        tag_explanation=validated.tag_explanation,
        preliminary_judgment=validated.preliminary_judgment,
        strengths=validated.strengths,
        risks=validated.risks,
        unlock_hint=validated.unlock_hint,
    )


def _build_item(assessment: Assessment, validated: UserReportSchema, followup_status: str | None = None) -> ReportListItem:
    return ReportListItem(
        assessment_id=assessment.id,
        status=assessment.status,
        branch=assessment.branch,
        tag=validated.tag,
        feasibility_score=validated.feasibility_score,
        display_score=validated.display_score,
        used_template_report=assessment.used_template_report,
        created_at=assessment.created_at,
        completed_at=assessment.completed_at,
        followup_status=followup_status,
    )


async def list_user_reports(
    db: AsyncSession,
    anonymous_user_id: str | None = None,
    limit: int = 20,
) -> list[ReportListItem]:
    if not anonymous_user_id:
        return []

    query = (
        select(Assessment, UserReportModel, LeadSubmission)
        .join(UserReportModel, UserReportModel.assessment_id == Assessment.id)
        .join(User, User.id == Assessment.user_id)
        .outerjoin(LeadSubmission, LeadSubmission.assessment_id == Assessment.id)
        .where(User.wechat_openid == _wechat_openid_from_anonymous(anonymous_user_id))
        .order_by(Assessment.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()

    items: list[ReportListItem] = []
    for assessment, user_report_model, lead_sub in rows:
        validated = UserReportSchema.model_validate(user_report_model.report_json)
        followup_status = lead_sub.followup_status if lead_sub else None
        items.append(_build_item(assessment, validated, followup_status))
    return items


async def get_user_report_detail(
    db: AsyncSession,
    assessment_id: UUID,
    anonymous_user_id: str | None = None,
) -> ReportDetailResponse | None:
    if not anonymous_user_id:
        return None

    query = (
        select(Assessment, UserReportModel, LeadSubmission)
        .join(UserReportModel, UserReportModel.assessment_id == Assessment.id)
        .join(User, User.id == Assessment.user_id)
        .outerjoin(LeadSubmission, LeadSubmission.assessment_id == Assessment.id)
        .where(Assessment.id == assessment_id)
        .where(User.wechat_openid == _wechat_openid_from_anonymous(anonymous_user_id))
    )
    result = await db.execute(query)
    row = result.one_or_none()
    if row is None:
        return None

    assessment, user_report_model, lead_sub = row
    validated = UserReportSchema.model_validate(user_report_model.report_json)
    followup_status = lead_sub.followup_status if lead_sub else None
    is_unlocked = lead_sub is not None

    return ReportDetailResponse(
        assessment_id=assessment.id,
        status=assessment.status,
        branch=assessment.branch,
        used_template_report=assessment.used_template_report,
        created_at=assessment.created_at,
        completed_at=assessment.completed_at,
        is_unlocked=is_unlocked,
        report_summary=_build_summary(validated),
        user_report=validated if is_unlocked else None,
        followup_status=followup_status,
    )


async def list_user_reports_by_user_id(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 20,
) -> list[ReportListItem]:
    query = (
        select(Assessment, UserReportModel, LeadSubmission)
        .join(UserReportModel, UserReportModel.assessment_id == Assessment.id)
        .outerjoin(LeadSubmission, LeadSubmission.assessment_id == Assessment.id)
        .where(Assessment.user_id == user_id)
        .order_by(Assessment.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()

    items: list[ReportListItem] = []
    for assessment, user_report_model, lead_sub in rows:
        validated = UserReportSchema.model_validate(user_report_model.report_json)
        followup_status = lead_sub.followup_status if lead_sub else None
        items.append(_build_item(assessment, validated, followup_status))
    return items


async def get_user_report_detail_by_user_id(
    db: AsyncSession,
    assessment_id: UUID,
    user_id: UUID,
) -> ReportDetailResponse | None:
    query = (
        select(Assessment, UserReportModel, LeadSubmission)
        .join(UserReportModel, UserReportModel.assessment_id == Assessment.id)
        .outerjoin(LeadSubmission, LeadSubmission.assessment_id == Assessment.id)
        .where(Assessment.id == assessment_id)
        .where(Assessment.user_id == user_id)
    )
    result = await db.execute(query)
    row = result.one_or_none()
    if row is None:
        return None

    assessment, user_report_model, lead_sub = row
    validated = UserReportSchema.model_validate(user_report_model.report_json)
    followup_status = lead_sub.followup_status if lead_sub else None
    is_unlocked = lead_sub is not None

    return ReportDetailResponse(
        assessment_id=assessment.id,
        status=assessment.status,
        branch=assessment.branch,
        used_template_report=assessment.used_template_report,
        created_at=assessment.created_at,
        completed_at=assessment.completed_at,
        is_unlocked=is_unlocked,
        report_summary=_build_summary(validated),
        user_report=validated if is_unlocked else None,
        followup_status=followup_status,
    )
