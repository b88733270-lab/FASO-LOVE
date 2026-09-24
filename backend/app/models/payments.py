"""Modèles de monétisation : abonnements Premium + transactions Mobile Money.

Concepts clés :
- Une transaction est un ORDRE DE PAIEMENT (Mobile Money / carte) avec
  machine à états : initiated → pending → succeeded | failed | cancelled.
- Un abonnement devient actif à la CONFIRMATION du paiement (webhook
  prestataire ou simulation sandbox) — jamais à l'initiation.
- Idempotence à deux niveaux : requête checkout (fenêtre 15 min) et
  événement webhook (provider_event_id unique).
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import utcnow
from app.db.base import Base


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # "orange_money" | "moov" | "stripe" | "mock"
    provider: Mapped[str] = mapped_column(String(20))
    plan_code: Mapped[str] = mapped_column(String(30))
    amount_fcfa: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="XOF")
    phone_e164: Mapped[str] = mapped_column(String(16))
    # initiated | pending | succeeded | failed | cancelled | refunded
    status: Mapped[str] = mapped_column(String(15), default="initiated", index=True)
    provider_ref: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True
    )
    checkout_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Dédup des événements webhook (certains agrégateurs rejouent).
    provider_event_id: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True
    )
    failure_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
    succeeded_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("ix_txn_user_status", "user_id", "status"),
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    plan_code: Mapped[str] = mapped_column(String(30))
    # active | expired | cancelled
    status: Mapped[str] = mapped_column(String(15), default="active", index=True)
    starts_at: Mapped[datetime] = mapped_column(default=utcnow)
    ends_at: Mapped[datetime] = mapped_column()
    source_payment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("payment_transactions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    __table_args__ = (
        UniqueConstraint("source_payment_id", name="uq_subscription_payment"),
        Index("ix_sub_user_status_ends", "user_id", "status", "ends_at"),
    )
