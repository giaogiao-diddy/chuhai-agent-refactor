from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.conversation import router as conversation_router
from app.api.health import router as health_router
from config import get_settings

settings = get_settings()


def _parse_cors_origins(raw: str) -> list[str]:
    """解析 CORS 来源配置。"""
    stripped = raw.strip()
    if stripped == "*":
        return ["*"]
    return [origin.strip() for origin in stripped.split(",") if origin.strip()]


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
    )

    origins = _parse_cors_origins(settings.CORS_ORIGINS)
    allow_credentials = origins != ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 路由挂载
    app.include_router(health_router)
    app.include_router(conversation_router)

    return app


app = create_app()
