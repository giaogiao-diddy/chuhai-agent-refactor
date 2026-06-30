import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Assessment, LeadSubmission, User
from app.models.report import UserReport as UserReportModel


async def create_lead_submission(
    db: AsyncSession,
    assessment_id: uuid.UUID,
    anonymous_user_id: str,
    contact_name: str,
    phone: str,
    wechat_id: str | None = None,
    company_name: str | None = None,
    note: str | None = None,
) -> LeadSubmission:
    wechat_openid = f"anonymous:{anonymous_user_id}"

    user_result = await db.execute(
        select(User).where(User.wechat_openid == wechat_openid)
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise LookupError

    assess_result = await db.execute(
        select(Assessment).where(
            Assessment.id == assessment_id,
            Assessment.user_id == user.id,
        )
    )
    assessment = assess_result.scalar_one_or_none()
    if assessment is None:
        raise LookupError

    ur_result = await db.execute(
        select(UserReportModel).where(UserReportModel.assessment_id == assessment_id)
    )
    if ur_result.scalar_one_or_none() is None:
        raise LookupError

    stmt = (
        insert(LeadSubmission)
        .values(
            assessment_id=assessment_id,
            user_id=user.id,
            contact_name=contact_name,
            phone=phone,
            wechat_id=wechat_id,
            company_name=company_name,
            note=note,
        )
        .on_conflict_do_nothing(index_elements=[LeadSubmission.assessment_id])
        .returning(LeadSubmission.id)
    )
    result = await db.execute(stmt)
    created_id = result.scalar_one_or_none()

    if created_id is not None:
        submission = await db.get(LeadSubmission, created_id)
        if submission is None:
            raise ValueError
        return submission

    existing = await db.scalar(
        select(LeadSubmission).where(LeadSubmission.assessment_id == assessment_id)
    )
    if existing is None:
        raise ValueError
    return existing


async def create_lead_submission_for_user(
    db: AsyncSession,
    assessment_id: uuid.UUID,
    user_id: uuid.UUID,
    contact_name: str,
    phone: str,
    wechat_id: str | None = None,
    company_name: str | None = None,
    note: str | None = None,
) -> LeadSubmission:
    assess_result = await db.execute(
        select(Assessment).where(
            Assessment.id == assessment_id,
            Assessment.user_id == user_id,
        )
    )
    if assess_result.scalar_one_or_none() is None:
        raise LookupError

    ur_result = await db.execute(
        select(UserReportModel).where(UserReportModel.assessment_id == assessment_id)
    )
    if ur_result.scalar_one_or_none() is None:
        raise LookupError

    stmt = (
        insert(LeadSubmission)
        .values(
            assessment_id=assessment_id,
            user_id=user_id,
            contact_name=contact_name,
            phone=phone,
            wechat_id=wechat_id,
            company_name=company_name,
            note=note,
        )
        .on_conflict_do_nothing(index_elements=[LeadSubmission.assessment_id])
        .returning(LeadSubmission.id)
    )
    result = await db.execute(stmt)
    created_id = result.scalar_one_or_none()

    if created_id is not None:
        submission = await db.get(LeadSubmission, created_id)
        if submission is None:
            raise ValueError
        return submission

    existing = await db.scalar(
        select(LeadSubmission).where(LeadSubmission.assessment_id == assessment_id)
    )
    if existing is None:
        raise ValueError
    return existing
