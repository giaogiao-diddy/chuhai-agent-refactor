from __future__ import annotations
"""留资与转发接口"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.assessment import Assessment
from app.models.share_record import ShareRecord
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
    """提交留资信息 — 校验归属 + 完成状态，解锁对应测评报告"""
    assessment = db.query(Assessment).filter_by(
        id=body.assessment_id,
        user_id=current_user["user_id"],
    ).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="测评不存在")
    if assessment.status != "completed":
        raise HTTPException(status_code=400, detail="测评尚未完成，无法留资")

    result = create_lead(
        db,
        user_id=current_user["user_id"],
        assessment_id=body.assessment_id,
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
    """记录转发行为 — 奖励 10 分钟，增加顾问解读权益"""
    # 校验测评存在且属于当前用户
    assessment = db.query(Assessment).filter_by(id=body.assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="测评不存在")
    if assessment.user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="无权操作此测评")
    if assessment.status != "completed":
        raise HTTPException(status_code=400, detail="测评尚未完成，无法转发")

    # 写入转发记录
    share = ShareRecord(
        user_id=current_user["user_id"],
        assessment_id=body.assessment_id,
        share_scene=body.share_scene,
        reward_minutes=10,
    )
    db.add(share)

    # 更新权益分钟数
    assessment.benefit_minutes = (assessment.benefit_minutes or 45) + 10
    db.commit()

    return ShareRecordResponse(
        reward_minutes=10,
        total_benefit_minutes=assessment.benefit_minutes,
    )
