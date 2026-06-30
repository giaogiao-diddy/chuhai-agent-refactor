import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import get_current_user_optional
from app.db.session import get_db
from app.models import User
from app.schemas.lead_submission import LeadSubmissionCreate, LeadSubmissionResponse
from app.services.lead_submission_repository import create_lead_submission, create_lead_submission_for_user

router = APIRouter(prefix="/reports", tags=["lead-submission"])


@router.post("/{assessment_id}/lead-submission", response_model=LeadSubmissionResponse)
async def submit_lead(
    assessment_id: uuid.UUID,
    payload: LeadSubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    try:
        if current_user is not None:
            submission = await create_lead_submission_for_user(
                db,
                assessment_id=assessment_id,
                user_id=current_user.id,
                contact_name=payload.contact_name,
                phone=payload.phone,
                wechat_id=payload.wechat_id,
                company_name=payload.company_name,
                note=payload.note,
            )
        elif payload.anonymous_user_id:
            submission = await create_lead_submission(
                db,
                assessment_id=assessment_id,
                anonymous_user_id=payload.anonymous_user_id,
                contact_name=payload.contact_name,
                phone=payload.phone,
                wechat_id=payload.wechat_id,
                company_name=payload.company_name,
                note=payload.note,
            )
        else:
            raise HTTPException(status_code=401, detail="请先登录")
    except LookupError:
        raise HTTPException(status_code=404, detail="报告不存在或无权提交")
    except ValueError:
        raise HTTPException(status_code=422, detail="请检查联系方式")

    return LeadSubmissionResponse(
        submission_id=str(submission.id),
        assessment_id=str(submission.assessment_id),
        submitted=True,
        created_at=submission.created_at,
    )
