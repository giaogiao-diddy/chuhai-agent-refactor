"""create model_providers table

Revision ID: 20260701_model_providers
Revises: None
Create Date: 2026-07-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260701_model_providers"
down_revision: Union[str, None] = "0006_add_lead_followup_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("provider_type", sa.String(32), nullable=False, server_default="openai_compatible"),
        sa.Column("base_url", sa.String(512), nullable=False),
        sa.Column("api_key", sa.Text, nullable=False),
        sa.Column("default_model", sa.String(128), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("context_window", sa.Integer, nullable=False, server_default="128000"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("model_providers")
