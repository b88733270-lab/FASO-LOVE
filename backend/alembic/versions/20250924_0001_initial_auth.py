"""Schéma initial — authentification FASO LOVE (users, otp_codes, refresh_tokens).

Revision ID: 0001_initial_auth
Revises:
Create Date: 2025-09-24

Phase 1 : identité minimale conforme au plan de transformation.
Le profil riche (photos, bio, géolocalisation PostGIS…) arrive en phase 2.
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_auth"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("birthdate", sa.Date(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_phone_e164", "users", ["phone_e164"], unique=True)

    op.create_table(
        "otp_codes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("is_consumed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_otp_codes_phone_e164", "otp_codes", ["phone_e164"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index("ix_otp_codes_phone_e164", table_name="otp_codes")
    op.drop_table("otp_codes")
    op.drop_index("ix_users_phone_e164", table_name="users")
    op.drop_table("users")
