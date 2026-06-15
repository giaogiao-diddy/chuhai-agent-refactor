from __future__ import annotations
"""FastAPI 依赖注入 — 用户认证、管理员鉴权"""

from fastapi import Depends, HTTPException, Header, status

from config import settings

try:
    import jwt
except ImportError:
    jwt = None


def get_current_user(
    authorization: str | None = Header(default=None),
) -> dict:
    """从 JWT Token 解析当前用户，未认证抛出 401。"""
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


def require_admin(current_user: dict = Depends(get_current_user)):
    """管理员鉴权 — admin_user_ids 为空时放行，否则校验 user_id"""
    admin_ids_str = (settings.admin_user_ids or "").strip()
    if not admin_ids_str:
        return current_user
    admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
    if current_user["user_id"] not in admin_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current_user
