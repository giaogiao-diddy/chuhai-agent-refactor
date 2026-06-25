from __future__ import annotations
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, func

from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False, unique=True)
    summary_report_json = Column(JSON, nullable=True)
    full_report_json = Column(JSON, nullable=True)
    is_unlocked = Column(Boolean, default=False)
    generation_type = Column(String(16), default="ai")  # ai / template
    ai_model = Column(String(64), nullable=True)
    prompt_version = Column(String(32), nullable=True)
    generation_status = Column(String(16), default="pending")  # pending / generating / success / failed
    generation_error = Column(String(512), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
