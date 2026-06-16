from __future__ import annotations
"""后台管理接口"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.lead import Lead
from app.models.assessment import Assessment
from app.models.answer import Answer
from app.models.report import Report
from app.models.ai_report_log import AIReportLog
from app.schemas.admin import (
    LeadDetailResponse,
    AssessmentDetailResponse,
    AIReportLogResponse,
    FollowNoteCreate,
)

router = APIRouter(tags=["admin"])


@router.get("/admin/leads", response_model=list[LeadDetailResponse])
def list_leads(
    page: int = 1,
    size: int = 20,
    tag: str | None = None,
    is_unlocked: bool | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """后台线索列表 — 支持按标签、留资状态筛选"""
    query = db.query(Lead)
    if is_unlocked is not None:
        query = query.join(Report, Lead.assessment_id == Report.assessment_id).filter(
            Report.is_unlocked == is_unlocked
        )
    offset = (page - 1) * size
    leads = query.offset(offset).limit(size).all()
    result = []
    for lead in leads:
        assessment = db.query(Assessment).filter_by(id=lead.assessment_id).first()
        report = db.query(Report).filter_by(assessment_id=lead.assessment_id).first()
        result.append(
            LeadDetailResponse(
                id=lead.id,
                name=lead.name,
                contact=lead.contact,
                company=lead.company,
                role=lead.role,
                assessment_id=lead.assessment_id,
                total_score=assessment.total_score if assessment else None,
                tag=assessment.tag if assessment else None,
                is_unlocked=report.is_unlocked if report else False,
                created_at=str(lead.created_at) if lead.created_at else None,
            )
        )
    return result


@router.get("/admin/assessments/{assessment_id}", response_model=AssessmentDetailResponse)
def get_assessment_detail(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """后台测评详情 — 查看测评答案和报告"""
    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="测评不存在")

    answers = db.query(Answer).filter_by(assessment_id=assessment_id).all()
    report = db.query(Report).filter_by(assessment_id=assessment_id).first()

    return AssessmentDetailResponse(
        id=assessment.id,
        user_id=assessment.user_id,
        total_score=assessment.total_score,
        tag=assessment.tag,
        status=assessment.status or "in_progress",
        answers=[{"question_id": a.question_id, "option_id": a.option_id, "score": a.score} for a in answers],
        report=report.summary_report_json if report else None,
        created_at=str(assessment.created_at) if assessment.created_at else None,
        completed_at=str(assessment.completed_at) if assessment.completed_at else None,
    )


@router.get("/admin/ai-report-logs", response_model=list[AIReportLogResponse])
def list_ai_report_logs(
    page: int = 1,
    size: int = 20,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """AI 调用日志列表"""
    query = db.query(AIReportLog)
    if status:
        query = query.filter_by(status=status)
    offset = (page - 1) * size
    logs = query.order_by(AIReportLog.id.desc()).offset(offset).limit(size).all()
    return [
        AIReportLogResponse(
            id=log.id,
            assessment_id=log.assessment_id,
            model=log.model,
            status=log.status or "pending",
            error_message=log.error_message,
            latency_ms=log.latency_ms,
            created_at=str(log.created_at) if log.created_at else None,
        )
        for log in logs
    ]


@router.post("/admin/follow-notes")
def create_follow_note(
    body: FollowNoteCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """创建跟进备注"""
    from app.models.follow_note import FollowNote
    note = FollowNote(lead_id=body.lead_id, owner=str(current_user["user_id"]), status=body.status, remark=body.remark)
    db.add(note)
    db.commit()
    return {"id": note.id, "status": "created"}
