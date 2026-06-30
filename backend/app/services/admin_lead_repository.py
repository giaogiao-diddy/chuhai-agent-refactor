from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Assessment, LeadSubmission
from app.models.report import LeadReport as LeadReportModel
from app.models.report import UserReport as UserReportModel
from app.schemas.admin_lead import AdminLeadDetail, AdminLeadListItem
from app.schemas.report import LeadReport as LeadReportSchema
from app.schemas.report import UserReport as UserReportSchema

# P0=0, P1=1, P2=2, P3=3, None/其他=4
PRIORITY_RANK = case(
    (Assessment.lead_priority == "P0", 0),
    (Assessment.lead_priority == "P1", 1),
    (Assessment.lead_priority == "P2", 2),
    (Assessment.lead_priority == "P3", 3),
    else_=4,
)


async def list_admin_leads(
    db: AsyncSession,
    limit: int = 50,
    followup_status: str | None = None,
) -> list[AdminLeadListItem]:
    query = (
        select(LeadSubmission, Assessment)
        .join(Assessment, Assessment.id == LeadSubmission.assessment_id)
    )
    if followup_status is not None:
        query = query.where(LeadSubmission.followup_status == followup_status)
    query = query.order_by(PRIORITY_RANK, LeadSubmission.created_at.desc()).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    items: list[AdminLeadListItem] = []
    for sub, assess in rows:
        items.append(AdminLeadListItem(
            submission_id=str(sub.id),
            assessment_id=str(sub.assessment_id),
            contact_name=sub.contact_name,
            phone=sub.phone,
            wechat_id=sub.wechat_id,
            company_name=sub.company_name,
            created_at=sub.created_at,
            tag=assess.tag,
            feasibility_score=assess.feasibility_score,
            display_score=assess.display_score,
            lead_priority=assess.lead_priority,
            used_template_report=assess.used_template_report,
            report_completed_at=assess.completed_at,
            followup_status=sub.followup_status,
        ))
    return items


async def get_admin_lead_detail(
    db: AsyncSession, submission_id: UUID
) -> AdminLeadDetail | None:
    query = (
        select(LeadSubmission, Assessment, UserReportModel, LeadReportModel)
        .join(Assessment, Assessment.id == LeadSubmission.assessment_id)
        .join(UserReportModel, UserReportModel.assessment_id == Assessment.id)
        .join(LeadReportModel, LeadReportModel.assessment_id == Assessment.id)
        .where(LeadSubmission.id == submission_id)
    )
    result = await db.execute(query)
    row = result.one_or_none()
    if row is None:
        return None

    sub, assess, ur_model, lr_model = row
    validated_ur = UserReportSchema.model_validate(ur_model.report_json)
    validated_lr = LeadReportSchema.model_validate(lr_model.report_json)
    return AdminLeadDetail(
        submission_id=str(sub.id),
        assessment_id=str(sub.assessment_id),
        contact_name=sub.contact_name,
        phone=sub.phone,
        wechat_id=sub.wechat_id,
        company_name=sub.company_name,
        note=sub.note,
        created_at=sub.created_at,
        tag=assess.tag,
        feasibility_score=assess.feasibility_score,
        display_score=assess.display_score,
        lead_priority=assess.lead_priority,
        used_template_report=assess.used_template_report,
        report_completed_at=assess.completed_at,
        followup_status=sub.followup_status,
        followup_note=sub.followup_note,
        user_report=validated_ur,
        lead_report=validated_lr,
    )


async def update_lead_followup(
    db: AsyncSession,
    submission_id: UUID,
    followup_status: str,
    followup_note: str | None,
) -> AdminLeadDetail | None:
    sub = await db.get(LeadSubmission, submission_id)
    if sub is None:
        return None
    sub.followup_status = followup_status
    sub.followup_note = followup_note
    await db.flush()
    await db.refresh(sub)

    return await get_admin_lead_detail(db, submission_id)
