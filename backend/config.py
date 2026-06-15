from __future__ import annotations
"""全局配置中心 — 所有环境变量集中管理，通过 pydantic-settings 读取 .env"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── 数据库 ─────────────────────────────────────────────
    database_url: str = ""       # 设置后直接用作连接串（测试用 SQLite）
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "luobin_agent"

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    # ── LLM (DeepSeek) ─────────────────────────────────────
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_timeout: int = 15

    # ── JWT ────────────────────────────────────────────────
    jwt_secret: str = "your-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 72

    # ── Server ─────────────────────────────────────────────
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    port: int = 8000
    debug: bool = False

    # ── Admin ──────────────────────────────────────────────
    admin_user_ids: str = ""  # 逗号分隔的 user_id，为空时跳过管理员校验

    # ── WeChat ─────────────────────────────────────────────
    wx_appid: str = ""
    wx_secret: str = ""

    # ── 云托管 ─────────────────────────────────────────────
    cloudbase_env_id: str = ""

    # ── 报告 ───────────────────────────────────────────────
    ai_report_enabled: bool = True
    report_poll_interval: float = 1.5
    report_generate_timeout: int = 20

    class Config:
        env_file = ".env"
        env_prefix = "LB_"


settings = Settings()
