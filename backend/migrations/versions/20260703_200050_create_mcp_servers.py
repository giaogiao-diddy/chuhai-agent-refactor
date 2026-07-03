# create mcp_servers table
#
# Revision ID: 20260703_200050
# Revises: 20260703
# Create Date: 2026-07-03T20:00:50.423274
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260703_200050"
down_revision: Union[str, None] = "20260703_142215"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mcp_servers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("transport", sa.String(16), nullable=False, server_default="http"),
        sa.Column("url", sa.String(512), nullable=True),
        sa.Column("command", sa.String(512), nullable=True),
        sa.Column("args", postgresql.JSONB, server_default="[]"),
        sa.Column("env", postgresql.JSONB, server_default="{}"),
        sa.Column("headers", postgresql.JSONB, server_default="{}"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("mcp_servers")
