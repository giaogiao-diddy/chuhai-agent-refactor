from __future__ import annotations
"""FastAPI 应用入口 — 创建 app、挂载路由、注册中间件、lifespan"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import logging

from app.api import auth, questions, assessments, reports, leads, admin
from app.core.middleware import RequestLoggingMiddleware
from app.core.database import init_db

logger = logging.getLogger("luobin")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期 — 尝试建表，失败不阻塞启动"""
    try:
        init_db()
        logger.info("数据库表初始化完成")
    except Exception as e:
        logger.warning("数据库表初始化失败（可能 MySQL 未就绪）: %s", e)
    yield


app = FastAPI(
    title="罗宾出海分析 Agent",
    description="出海机会测评获客系统 API",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 请求日志中间件 ────────────────────────────────────────
app.add_middleware(RequestLoggingMiddleware)

# ── 路由挂载 ──────────────────────────────────────────────
app.include_router(auth.router, prefix="/api")
app.include_router(questions.router, prefix="/api")
app.include_router(assessments.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(leads.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/health")
def health_check():
    """健康检查端点"""
    return {"status": "ok"}
