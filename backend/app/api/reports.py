from __future__ import annotations
"""报告查询接口"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.assessment import Assessment
from app.models.report import Report
from app.schemas.report import SummaryReport, FullReport, MyReportResponse

router = APIRouter(tags=["reports"])


@router.get("/reports/{assessment_id}/summary")
def get_summary_report(assessment_id: int, db: Session = Depends(get_db)):
    """获取部分报告（无需留资，公开访问）"""
    report = db.query(Report).filter_by(assessment_id=assessment_id).first()
    if not report or not report.summary_report_json:
        raise HTTPException(status_code=404, detail="报告不存在或尚未生成")
    return report.summary_report_json


@router.get("/reports/my", response_model=MyReportResponse)
def get_my_report(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """我的报告 — 返回最近一次已完成测评的报告卡片"""
    assessment = (
        db.query(Assessment)
        .filter_by(user_id=current_user["user_id"], status="completed")
        .order_by(Assessment.completed_at.desc())
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="暂无已完成测评报告")

    report = db.query(Report).filter_by(assessment_id=assessment.id).first()

    return MyReportResponse(
        assessment_id=assessment.id,
        total_score=assessment.total_score or 0,
        tag=assessment.tag or "",
        display_score=min((assessment.total_score or 0) + 45, 100),
        completed_at=str(assessment.completed_at) if assessment.completed_at else None,
        summary=report.summary_report_json if report else None,
    )


@router.get("/reports/{assessment_id}/full")
def get_full_report(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取完整报告 — 需留资解锁 + 归属校验，否则返回 403"""
    # 先校验测评属于当前用户
    assessment = db.query(Assessment).filter_by(
        id=assessment_id,
        user_id=current_user["user_id"],
    ).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="报告不存在")

    report = db.query(Report).filter_by(assessment_id=assessment_id).first()
    if not report or not report.full_report_json:
        raise HTTPException(status_code=404, detail="报告不存在或尚未生成")
    if not report.is_unlocked:
        raise HTTPException(status_code=403, detail="请先提交信息解锁完整报告")
    return report.full_report_json
