"""Phase 3 — likes, matchs réciproques, blocages.

Revision ID: 0003_interactions
Revises: 0002_profiles
Create Date: 2025-09-24
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_interactions"
down_revision = "0002_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "likes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("from_user_id", sa.String(length=36), nullable=False),
        sa.Column("to_user_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=12), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("from_user_id", "to_user_id", name="uq_like_pair"),
        sa.ForeignKey("from_user_id", ["users.id"], ondelete="CASCADE"),
        sa.ForeignKey("to_user_id", ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_likes_from_user_id", "likes", ["from_user_id"])
    op.create_index("ix_likes_to_user_id", "likes", ["to_user_id"])

    op.create_table(
        "matches",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_low", sa.String(length=36), nullable=False),
        sa.Column("user_high", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_low", "user_high", name="uq_match_pair"),
        sa.ForeignKey("user_low", ["users.id"], ondelete="CASCADE"),
        sa.ForeignKey("user_high", ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_matches_user_low", "matches", ["user_low"])
    op.create_index("ix_matches_user_high", "matches", ["user_high"])

    op.create_table(
        "blocks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("blocker_id", sa.String(length=36), nullable=False),
        sa.Column("blocked_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_block_pair"),
        sa.ForeignKey("blocker_id", ["users.id"], ondelete="CASCADE"),
        sa.ForeignKey("blocked_id", ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_blocks_blocker_id", "blocks", ["blocker_id"])
    op.create_index("ix_blocks_blocked_id", "blocks", ["blocked_id"])


def downgrade() -> None:
    op.drop_table("blocks")
    op.drop_table("matches")
    op.drop_table("likes")
