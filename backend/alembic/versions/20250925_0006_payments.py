"""Phase 7 — monétisation : abonnements Premium + transactions Mobile Money.

Revision ID: 0006_payments
Revises: 0005_reports
Create Date: 2025-09-25
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_payments"
down_revision = "0005_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("plan_code", sa.String(length=30), nullable=False),
        sa.Column("amount_fcfa", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="XOF"),
        sa.Column("phone_e164", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=15), nullable=False, server_default="initiated"),
        sa.Column("provider_ref", sa.String(length=64), unique=True, nullable=True),
        sa.Column("checkout_url", sa.String(length=500), nullable=True),
        sa.Column("provider_event_id", sa.String(length=64), unique=True, nullable=True),
        sa.Column("failure_reason", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("succeeded_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_txn_user_status", "payment_transactions", ["user_id", "status"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan_code", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=15), nullable=False, server_default="active"),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column(
            "source_payment_id",
            sa.String(length=36),
            sa.ForeignKey("payment_transactions.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("source_payment_id", name="uq_subscription_payment"),
    )
    op.create_index(
        "ix_sub_user_status_ends", "subscriptions", ["user_id", "status", "ends_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_sub_user_status_ends", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index("ix_txn_user_status", table_name="payment_transactions")
    op.drop_table("payment_transactions")
