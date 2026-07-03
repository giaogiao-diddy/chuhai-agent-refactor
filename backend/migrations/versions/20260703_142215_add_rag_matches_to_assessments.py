"""add rag_matches to assessments

Revision ID: 20260703_142215
Revises: 20260703_124655
Create Date: 2026-07-03T14:22:15.364928
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260703_142215"
down_revision: Union[str, None] = "20260703_124655"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column("rag_matches", postgresql.JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("assessments", "rag_matches")
