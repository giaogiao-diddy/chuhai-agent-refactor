import uuid

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_access_token
from app.db.session import get_db
from app.models import User


async def get_current_user_optional(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    try:
        payload = decode_access_token(token)
    except ValueError:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    try:
        user = await db.get(User, uuid.UUID(user_id))
    except (ValueError, TypeError):
        return None
    return user


async def get_current_user_required(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await get_current_user_optional(authorization=authorization, db=db)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录")
    return user


async def get_current_consultant_required(
    user: User = Depends(get_current_user_required),
) -> User:
    if user.role not in ("consultant", "admin"):
        raise HTTPException(status_code=403, detail="无权访问")
    return user
