import uuid
from datetime import datetime, timezone

from datetime import timezone as tz

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=True)
    branch: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    conversation_round: Mapped[int] = mapped_column(Integer, default=0)
    ai_failure_count: Mapped[int] = mapped_column(Integer, default=0)
    validation_errors: Mapped[list] = mapped_column(JSONB, default=list)
    slots: Mapped[dict] = mapped_column(JSONB, default=dict)
    answers: Mapped[dict] = mapped_column(JSONB, default=dict)
    scoring_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    feasibility_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lead_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    display_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lead_priority: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    audit_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    report_retry_count: Mapped[int] = mapped_column(Integer, default=0)
    used_template_report: Mapped[bool] = mapped_column(Boolean, default=False)
    report_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    scoring_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rag_matches: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(tz.utc), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(tz.utc), onupdate=lambda: datetime.now(tz.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
