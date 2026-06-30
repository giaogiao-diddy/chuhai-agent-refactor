"""create lead_submissions

Revision ID: 0003
Revises: 0002_create_core_tables
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_create_lead_submissions"
down_revision: str | None = "0002_create_core_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lead_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id"), nullable=False, unique=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("contact_name", sa.String(50), nullable=False),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("wechat_id", sa.String(80), nullable=True),
        sa.Column("company_name", sa.String(100), nullable=True),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_lead_submissions_assessment_id", "lead_submissions", ["assessment_id"])
    op.create_index("ix_lead_submissions_user_id", "lead_submissions", ["user_id"])


def downgrade() -> None:
    op.drop_table("lead_submissions")
