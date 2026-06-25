from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置，从环境变量 / .env 文件读取。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── 应用基础 ──
    APP_NAME: str = "chuhai-agent"
    APP_VERSION: str = "0.1.0"
    ENV: str = "development"

    # ── 数据库 ──
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/chuhai_agent"

    # ── CORS ──
    CORS_ORIGINS: str = "*"

    # ── 鉴权 ──
    JWT_SECRET_KEY: str = ""
    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""

    # ── AI ──
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"
    DEEPSEEK_EMBEDDING_MODEL: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"


@lru_cache
def get_settings() -> Settings:
    """返回全局唯一的 Settings 实例（lru_cache 保证单例）。"""
    return Settings()
