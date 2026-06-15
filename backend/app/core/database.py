"""数据库连接与 Session 管理 — 同步 SQLAlchemy 2.0"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings


def _build_engine_kwargs(db_url: str) -> dict:
    """根据数据库类型返回合适的 create_engine 参数。"""
    if "sqlite" in db_url:
        return {
            "connect_args": {"check_same_thread": False},
            "echo": settings.debug,
        }
    # MySQL / PostgreSQL
    return {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "echo": settings.debug,
    }


engine = create_engine(settings.db_url, **_build_engine_kwargs(settings.db_url))

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db():
    """FastAPI 依赖注入 — 每个请求获取独立 session，结束后关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(engine_override=None):
    """创建全部 ORM 表 — 幂等（已有表不重复创建）"""
    import app.models.user  # noqa: F401
    import app.models.question  # noqa: F401
    import app.models.assessment  # noqa: F401
    import app.models.answer  # noqa: F401
    import app.models.report  # noqa: F401
    import app.models.lead  # noqa: F401
    import app.models.share_record  # noqa: F401
    import app.models.follow_note  # noqa: F401
    import app.models.admin_user  # noqa: F401
    import app.models.ai_report_log  # noqa: F401
    target = engine_override or engine
    Base.metadata.create_all(bind=target)
