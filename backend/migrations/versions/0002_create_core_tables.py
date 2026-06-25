"""create core tables: users, assessments, messages, user_reports, lead_reports

Revision ID: 0002
Revises: 0001_enable_pgvector
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_create_core_tables"
down_revision: str | None = "0001_enable_pgvector"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("wechat_openid", sa.String(128), unique=True, nullable=True),
        sa.Column("nickname", sa.String(128), nullable=True),
        sa.Column("role", sa.String(32), server_default="user"),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("branch", sa.String(32), nullable=True),
        sa.Column("status", sa.String(32), server_default="active"),
        sa.Column("conversation_round", sa.Integer(), server_default="0"),
        sa.Column("ai_failure_count", sa.Integer(), server_default="0"),
        sa.Column("validation_errors", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("slots", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("answers", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("scoring_result", postgresql.JSONB(), nullable=True),
        sa.Column("feasibility_score", sa.Integer(), nullable=True),
        sa.Column("lead_score", sa.Integer(), nullable=True),
        sa.Column("display_score", sa.Integer(), nullable=True),
        sa.Column("tag", sa.String(64), nullable=True),
        sa.Column("lead_priority", sa.String(16), nullable=True),
        sa.Column("audit_result", postgresql.JSONB(), nullable=True),
        sa.Column("report_retry_count", sa.Integer(), server_default="0"),
        sa.Column("used_template_report", sa.Boolean(), server_default=sa.false()),
        sa.Column("report_error", sa.Text(), nullable=True),
        sa.Column("scoring_error", sa.Text(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_assessments_user_id", "assessments", ["user_id"])
    op.create_index("ix_assessments_status", "assessments", ["status"])
    op.create_index("ix_assessments_lead_priority", "assessments", ["lead_priority"])
    op.create_index("ix_assessments_created_at", "assessments", ["created_at"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id"), nullable=False),
        sa.Column("role", sa.String(16)),
        sa.Column("content", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_messages_assessment_id", "messages", ["assessment_id"])

    op.create_table(
        "user_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id"), nullable=False, unique=True),
        sa.Column("report_json", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "lead_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id"), nullable=False, unique=True),
        sa.Column("report_json", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("lead_reports")
    op.drop_table("user_reports")
    op.drop_table("messages")
    op.drop_table("assessments")
    op.drop_table("users")
