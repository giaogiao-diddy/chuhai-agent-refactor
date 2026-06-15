from __future__ import annotations
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func

from app.core.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    name = Column(String(32), nullable=False)
    contact = Column(String(64), nullable=False)
    company = Column(String(128), nullable=False)
    role = Column(String(64), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
