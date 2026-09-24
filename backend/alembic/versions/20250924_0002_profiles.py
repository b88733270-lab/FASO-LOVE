"""Phase 2 — profils et photos avec file de modération.

Revision ID: 0002_profiles
Revises: 0001_initial_auth
Create Date: 2025-09-24
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_profiles"
down_revision = "0001_initial_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("display_name", sa.String(length=60), nullable=False),
        sa.Column("gender", sa.String(length=10), nullable=False),
        sa.Column("looking_for", sa.String(length=10), nullable=False),
        sa.Column("bio", sa.String(length=500), nullable=False),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("interests", sa.JSON(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "profile_photos",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_path", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_profile_photos_user_id", "profile_photos", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_profile_photos_user_id", table_name="profile_photos")
    op.drop_table("profile_photos")
    op.drop_table("profiles")
