from __future__ import annotations
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_score = Column(Integer, nullable=True)
    tag = Column(String(32), nullable=True)
    status = Column(String(16), default="in_progress")  # in_progress / completed
    benefit_minutes = Column(Integer, default=45)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)

    answers = relationship("Answer")
    report = relationship("Report", uselist=False)
