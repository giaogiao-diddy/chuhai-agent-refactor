from __future__ import annotations
"""报告查询接口"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.report import Report
from app.schemas.report import SummaryReport, FullReport

router = APIRouter(tags=["reports"])


@router.get("/reports/{assessment_id}/summary")
def get_summary_report(assessment_id: int, db: Session = Depends(get_db)):
    """获取部分报告（无需留资，公开访问）"""
    report = db.query(Report).filter_by(assessment_id=assessment_id).first()
    if not report or not report.summary_report_json:
        raise HTTPException(status_code=404, detail="报告不存在或尚未生成")
    return report.summary_report_json


@router.get("/reports/{assessment_id}/full")
def get_full_report(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取完整报告 — 需先留资解锁，否则返回 403"""
    report = db.query(Report).filter_by(assessment_id=assessment_id).first()
    if not report or not report.full_report_json:
        raise HTTPException(status_code=404, detail="报告不存在或尚未生成")
    if not report.is_unlocked:
        raise HTTPException(status_code=403, detail="请先提交信息解锁完整报告")
    return report.full_report_json
