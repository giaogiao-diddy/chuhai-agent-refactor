from __future__ import annotations
"""FastAPI 依赖注入 — 用户认证、管理员鉴权"""

import time

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from config import settings

try:
    import jwt
except ImportError:
    jwt = None


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    """从 JWT Token 解析当前用户，未认证抛出 401。

    Returns:
        {"user_id": int, "openid": str}
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证信息")

    token = authorization.replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证信息")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 Token")

    user_id = payload.get("sub")
    openid = payload.get("openid", "")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 Token")

    return {"user_id": int(user_id), "openid": openid}
