from __future__ import annotations
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func

from app.core.database import Base


class ShareRecord(Base):
    __tablename__ = "share_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    share_scene = Column(String(32), default="moment")
    reward_minutes = Column(Integer, default=10)
    created_at = Column(DateTime, server_default=func.now())
