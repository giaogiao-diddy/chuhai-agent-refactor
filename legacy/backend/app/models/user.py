from __future__ import annotations
from sqlalchemy import Column, Integer, String, DateTime, func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    openid = Column(String(128), unique=True, nullable=False, index=True)
    unionid = Column(String(128), nullable=True)
    nickname = Column(String(64), default="")
    avatar = Column(String(256), default="")
    created_at = Column(DateTime, server_default=func.now())
    last_login_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
