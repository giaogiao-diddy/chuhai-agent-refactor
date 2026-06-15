from __future__ import annotations
"""数据库连接与 Session 管理 — 同步 SQLAlchemy 2.0"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

engine = create_engine(
    settings.db_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.debug,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db():
    """FastAPI 依赖注入 — 每个请求获取独立 session，结束后关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
