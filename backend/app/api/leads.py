from __future__ import annotations
"""留资与转发接口"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.assessment import Assessment
from app.schemas.lead import LeadCreate, LeadResponse
from app.schemas.admin import ShareRecordCreate, ShareRecordResponse
from app.services.lead_service import create_lead

router = APIRouter(tags=["leads"])


@router.post("/leads", response_model=LeadResponse)
def submit_lead(
    body: LeadCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """提交留资信息，解锁最近一次完成的测评报告"""
    # 查找该用户最近完成的测评
    assessment = (
        db.query(Assessment)
        .filter_by(user_id=current_user["user_id"])
        .order_by(Assessment.id.desc())
        .first()
    )
    assessment_id = assessment.id if assessment else 1

    result = create_lead(
        db,
        user_id=current_user["user_id"],
        assessment_id=assessment_id,
        name=body.name,
        contact=body.contact,
        company=body.company,
        role=body.role,
    )
    return result


@router.post("/share-records", response_model=ShareRecordResponse)
def record_share(
    body: ShareRecordCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """记录转发行为，增加顾问解读分钟数"""
    # TODO: 写入 share_records 表，更新 assessment.benefit_minutes
    return ShareRecordResponse(reward_minutes=10, total_benefit_minutes=55)
