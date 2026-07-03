import uuid as _uuid
from datetime import datetime, timezone as tz

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class McpServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[_uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    transport: Mapped[str] = mapped_column(String(16), nullable=False, default="http")
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    command: Mapped[str | None] = mapped_column(String(512), nullable=True)
    args: Mapped[list] = mapped_column(JSONB, default=list)
    env: Mapped[dict] = mapped_column(JSONB, default=dict)
    headers: Mapped[dict] = mapped_column(JSONB, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(tz.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(tz.utc), onupdate=lambda: datetime.now(tz.utc))
