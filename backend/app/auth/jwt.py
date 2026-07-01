from datetime import datetime, timedelta, timezone

import jwt

from config import get_settings

# JWT_SECRET_KEY 最低长度（字符数）
_MIN_SECRET_LENGTH = 32

# 禁止使用的占位密钥
_BANNED_SECRETS = {
    "change_me",
    "your_jwt_secret_here",
    "your_secret_key",
}


def validate_jwt_secret() -> None:
    """校验 JWT_SECRET_KEY 是否安全可用。

    规则：
    - 不能为空字符串
    - 不能是常见占位值（change_me 等）
    - 长度不能短于 32 字符

    校验失败抛出 ValueError。
    注意：不把 secret 内容写入错误消息。
    """
    settings = get_settings()
    secret = settings.JWT_SECRET_KEY

    if not secret:
        raise ValueError("JWT_SECRET_KEY 未配置或为空")

    if secret.lower().strip() in _BANNED_SECRETS:
        raise ValueError("JWT_SECRET_KEY 仍为默认占位值，必须更换")

    if len(secret) < _MIN_SECRET_LENGTH:
        raise ValueError(
            f"JWT_SECRET_KEY 长度不足（需要至少 {_MIN_SECRET_LENGTH} 字符）"
        )


def create_access_token(user_id: str, role: str) -> str:
    settings = get_settings()
    validate_jwt_secret()
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    validate_jwt_secret()
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ValueError("token 已过期")
    except jwt.InvalidTokenError:
        raise ValueError("无效 token")
