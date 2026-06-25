from __future__ import annotations
"""企业微信解锁服务 — 查询/创建解锁会话/确认添加"""

from sqlalchemy.orm import Session

from fastapi import HTTPException, status

from app.models.assessment import Assessment
from app.models.report import Report
from config import settings


def get_unlock_status(db: Session, user_id: int, assessment_id: int) -> dict:
    """查询当前测评解锁状态"""
    assessment = db.query(Assessment).filter_by(
        id=assessment_id,
        user_id=user_id,
    ).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="测评不存在")
    if assessment.status != "completed":
        raise HTTPException(status_code=400, detail="测评尚未完成")

    report = db.query(Report).filter_by(assessment_id=assessment_id).first()
    full_report_available = report is not None and report.full_report_json is not None
    is_unlocked = report.is_unlocked if report else False

    return {
        "assessment_id": assessment_id,
        "is_unlocked": is_unlocked,
        "full_report_available": full_report_available,
        "message": "报告已解锁" if is_unlocked else "等待企微添加确认",
    }


def create_unlock_session(db: Session, user_id: int, assessment_id: int) -> dict:
    """创建企微解锁会话 — 返回二维码和轮询配置"""
    assessment = db.query(Assessment).filter_by(
        id=assessment_id,
        user_id=user_id,
    ).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="测评不存在")
    if assessment.status != "completed":
        raise HTTPException(status_code=400, detail="测评尚未完成")

    report = db.query(Report).filter_by(assessment_id=assessment_id).first()
    if report and report.is_unlocked:
        return {
            "assessment_id": assessment_id,
            "is_unlocked": True,
            "qr_code_url": None,
            "consultant_name": None,
            "polling_interval": settings.wecom_unlock_poll_interval,
            "message": "报告已解锁",
            "enable_mock_unlock": False,
        }

    return {
        "assessment_id": assessment_id,
        "is_unlocked": False,
        "qr_code_url": settings.wecom_qr_code_url or None,
        "consultant_name": settings.wecom_consultant_name or None,
        "polling_interval": settings.wecom_unlock_poll_interval,
        "message": "请添加企业微信顾问，添加成功后将自动解锁完整报告",
        "enable_mock_unlock": settings.enable_mock_wecom_unlock,
    }


def mark_wecom_added(
    db: Session,
    assessment_id: int,
    user_id: int | None = None,
    external_user_id: str | None = None,
    source: str = "wecom_callback",
) -> dict:
    """确认用户已添加企微 — 解锁报告"""
    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="测评不存在")

    # 如果有 user_id，校验归属
    if user_id is not None and assessment.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权操作此测评")

    report = db.query(Report).filter_by(assessment_id=assessment_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    if report.is_unlocked:
        return {"assessment_id": assessment_id, "is_unlocked": True, "already_unlocked": True}

    report.is_unlocked = True
    db.commit()

    return {"assessment_id": assessment_id, "is_unlocked": True, "already_unlocked": False, "source": source}
