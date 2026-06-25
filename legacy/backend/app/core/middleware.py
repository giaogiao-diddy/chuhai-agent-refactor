from __future__ import annotations
"""中间件 — 请求日志、速率限制、JWT 校验"""

import time
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("luobin")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """记录每个 HTTP 请求的方法、路径、状态码和耗时"""

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "%s %s → %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件（空壳，后续接入 Redis 或内存计数）"""

    async def dispatch(self, request: Request, call_next):
        # TODO: 实现单 IP 60 次/分钟限制
        return await call_next(request)
