"""Schémas de la monétisation (Phase 7) : offres, checkout, quotas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PlanOut(BaseModel):
    code: str
    titre: str
    prix_fcfa: int
    duree_jours: int
    avantages: list[str]


class WalletOut(BaseModel):
    provider: str
    libelle: str
    actif: bool  # mock en sandbox ; wallets réels once clés validées


class PlansOut(BaseModel):
    plans: list[PlanOut]
    wallets: list[WalletOut]
    gratuit: dict = Field(
        description="Quotas FREEMIUM du jour (likes, super_likes)."
    )


class CheckoutIn(BaseModel):
    plan_code: str
    provider: str = Field(description="orange_money | moov | mock")
    phone_e164: str | None = Field(
        default=None,
        description="Numéro du portefeuille ; défaut = téléphone du compte.",
    )


class CheckoutOut(BaseModel):
    transaction_id: str
    status: str
    instructions: str
    checkout_url: str | None = None


class QuotasOut(BaseModel):
    likes_used: int
    likes_limit: int | None  # None = illimité (Premium)
    super_likes_used: int
    super_likes_limit: int | None


class SubscriptionMeOut(BaseModel):
    is_premium: bool
    plan_code: str | None = None
    ends_at: datetime | None = None
    quotas: QuotasOut


class TransactionOut(BaseModel):
    id: str
    provider: str
    plan_code: str
    amount_fcfa: int
    currency: str = "XOF"
    status: str
    created_at: datetime
    succeeded_at: datetime | None = None

    class Config:
        from_attributes = True


class WebhookAckOut(BaseModel):
    detail: str = "ok"
    result: str


class WebhookPayload(BaseModel):
    """Charge normalisée (mock) ; les payloads prestataires réels passent
    par `gateway.verify_webhook()` avant normalisation."""

    txn_ref: str | None = None
    event_id: str | None = None
    status: str | None = None
    reason: str | None = None
    extra: dict[str, Any] | None = None


class SimulateOut(BaseModel):
    detail: str = "Paiement de démonstration traité."
    subscription_active: bool
