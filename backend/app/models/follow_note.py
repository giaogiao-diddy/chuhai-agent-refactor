from __future__ import annotations
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func

from app.core.database import Base


class FollowNote(Base):
    __tablename__ = "follow_notes"

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    owner = Column(String(64), nullable=False)
    status = Column(String(16), default="uncontacted")  # uncontacted / contacted / booked / closed / invalid
    remark = Column(String(512), default="")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
