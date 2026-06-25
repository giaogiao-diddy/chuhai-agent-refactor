from __future__ import annotations
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text, func

from app.core.database import Base


class AIReportLog(Base):
    __tablename__ = "ai_report_logs"

    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    question_id = Column(Integer, nullable=True)
    model = Column(String(64), nullable=False)
    prompt_version = Column(String(32), nullable=True)
    request_payload = Column(JSON, nullable=True)
    raw_response = Column(JSON, nullable=True)
    parsed_response = Column(JSON, nullable=True)
    diagnosis_tag = Column(JSON, nullable=True)
    report_memory = Column(Text, nullable=True)
    sales_hint = Column(Text, nullable=True)
    status = Column(String(16), default="pending")  # pending / success / failed
    error_message = Column(String(512), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
