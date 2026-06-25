"""v2 assessment ai memory

Revision ID: 20260616_v2_assessment_ai_memory
Revises:
Create Date: 2026-06-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260616_v2_assessment_ai_memory"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("questions", sa.Column("is_scored", sa.Boolean(), nullable=False, server_default=sa.true()))
    with op.batch_alter_table("answers") as batch_op:
        batch_op.alter_column("option_id", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column("answer_text", sa.Text(), nullable=True))
    op.add_column("ai_report_logs", sa.Column("question_id", sa.Integer(), nullable=True))
    op.add_column("ai_report_logs", sa.Column("diagnosis_tag", sa.JSON(), nullable=True))
    op.add_column("ai_report_logs", sa.Column("report_memory", sa.Text(), nullable=True))
    op.add_column("ai_report_logs", sa.Column("sales_hint", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("ai_report_logs", "sales_hint")
    op.drop_column("ai_report_logs", "report_memory")
    op.drop_column("ai_report_logs", "diagnosis_tag")
    op.drop_column("ai_report_logs", "question_id")
    with op.batch_alter_table("answers") as batch_op:
        batch_op.drop_column("answer_text")
        batch_op.alter_column("option_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("questions", "is_scored")
