from datetime import datetime, timedelta, timezone

import jwt

from config import get_settings


def create_access_token(user_id: str, role: str) -> str:
    settings = get_settings()
    if not settings.JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY 未配置")
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    if not settings.JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY 未配置")
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ValueError("token 已过期")
    except jwt.InvalidTokenError:
        raise ValueError("无效 token")
