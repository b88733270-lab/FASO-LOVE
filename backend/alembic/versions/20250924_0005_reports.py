"""Phase 5 — signalements (modération).

Revision ID: 0005_reports
Revises: 0004_messages
Create Date: 2025-09-24
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_reports"
down_revision = "0004_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("reporter_id", sa.String(length=36), nullable=False),
        sa.Column("reported_id", sa.String(length=36), nullable=False),
        sa.Column("reason", sa.String(length=30), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("resolution", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKey("reporter_id", ["users.id"], ondelete="CASCADE"),
        sa.ForeignKey("reported_id", ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_reports_reporter_id", "reports", ["reporter_id"])
    op.create_index("ix_reports_reported_id", "reports", ["reported_id"])


def downgrade() -> None:
    op.drop_index("ix_reports_reported_id", table_name="reports")
    op.drop_index("ix_reports_reporter_id", table_name="reports")
    op.drop_table("reports")
