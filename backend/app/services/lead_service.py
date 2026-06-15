from __future__ import annotations
"""留资 + 报告解锁服务"""

from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.report import Report


def create_lead(
    db: Session,
    user_id: int,
    assessment_id: int,
    name: str,
    contact: str,
    company: str,
    role: str,
) -> dict:
    """保存留资信息并解锁对应测评的完整报告

    Returns:
        {"lead_id": int, "unlocked": True, "benefit_minutes": 45}
    """
    lead = Lead(
        user_id=user_id,
        assessment_id=assessment_id,
        name=name,
        contact=contact,
        company=company,
        role=role,
    )
    db.add(lead)
    db.flush()

    # 解锁报告
    report = db.query(Report).filter_by(assessment_id=assessment_id).first()
    if report:
        report.is_unlocked = True

    db.commit()

    return {
        "lead_id": lead.id,
        "unlocked": True,
        "benefit_minutes": 45,
    }
