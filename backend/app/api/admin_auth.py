from fastapi import Header, HTTPException

from config import get_settings


async def require_admin(x_admin_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="admin api 未配置")
    if x_admin_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="未授权")
