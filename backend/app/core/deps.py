from __future__ import annotations
"""FastAPI 依赖注入 — 用户认证、管理员鉴权"""

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from app.core.database import get_db


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    """从 JWT Token 解析当前用户，未认证抛出 401

    Returns:
        {"user_id": int, "openid": str}
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证信息")
    token = authorization.replace("Bearer ", "")
    # TODO: 实际 JWT 解析待 auth_service 实现后接入
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT 解析待实现")
