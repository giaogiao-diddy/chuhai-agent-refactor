"""add provider_id model_name to assessments

Revision ID: 20260703_124655
Revises: 20260701_model_providers
Create Date: 2026-07-03T12:46:55.465831
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260703_124655"
down_revision: Union[str, None] = "20260701_model_providers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column("provider_id", sa.String(64), nullable=True))
    op.add_column("assessments", sa.Column("model_name", sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column("assessments", "model_name")
    op.drop_column("assessments", "provider_id")
