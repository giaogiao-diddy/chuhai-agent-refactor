# add followup_status and followup_note to lead_submissions
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_add_lead_followup_fields"
down_revision: str | None = "0005_add_user_avatar_url"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("lead_submissions", sa.Column("followup_status", sa.String(20), nullable=False, server_default="未联系"))
    op.add_column("lead_submissions", sa.Column("followup_note", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("lead_submissions", "followup_note")
    op.drop_column("lead_submissions", "followup_status")
