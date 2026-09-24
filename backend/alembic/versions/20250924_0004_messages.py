"""Phase 4 — messages de chat (conversation = match).

Revision ID: 0004_messages
Revises: 0003_interactions
Create Date: 2025-09-24
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_messages"
down_revision = "0003_interactions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("sender_id", sa.String(length=36), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.ForeignKey("match_id", ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKey("sender_id", ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_messages_match_created", "messages", ["match_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_messages_match_created", table_name="messages")
    op.drop_table("messages")
