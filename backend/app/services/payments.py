"""Monétisation FASO LOVE (Phase 7).

Flux Mobile Money burkinabè :
1. L'app crée un **checkout** (plan + portefeuille) → transaction `pending`,
   l'utilisateur reçoit la demande USSD sur son téléphone ;
2. L'agrégateur notifie le **webhook** (signature vérifiée) ;
3. `apply_payment_status()` active/renouvelle l'abonnement — **idempotent**
   (événement unique + statut déjà final).

Quotas FREEMIUM : comptage des likes du jour (00h00 UTC — cohérent avec des
utilisateurs au Burkina, GMT+0). Premium = vérifié par abonnement actif.
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from datetime import timedelta as td
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import utcnow
from app.models.interactions import Like
from app.models.payments import PaymentTransaction, Subscription
from app.models.user import User

# ----------------------------------------------------------------- catalogue


@dataclass(frozen=True)
class Plan:
    code: str
    titre: str
    prix_fcfa: int
    duree_jours: int
    avantages: tuple[str, ...] = field(default=())


PLAN_CATALOG: dict[str, Plan] = {
    "premium_week": Plan(
        code="premium_week",
        titre="Premium 7 jours",
        prix_fcfa=1500,
        duree_jours=7,
        avantages=(
            "Likes illimités",
            "Super likes illimités",
            "Badge Premium visible",
        ),
    ),
    "premium_month": Plan(
        code="premium_month",
        titre="Premium 30 jours",
        prix_fcfa=3500,
        duree_jours=30,
        avantages=(
            "Likes illimités",
            "Super likes illimités",
            "Badge Premium visible",
            "Profil mis en avant",
        ),
    ),
    "premium_3m": Plan(
        code="premium_3m",
        titre="Premium 3 mois",
        prix_fcfa=9000,
        duree_jours=90,
        avantages=(
            "Likes illimités",
            "Super likes illimités",
            "Badge Premium visible",
            "Profil mis en avant",
            "Support prioritaire",
        ),
    ),
}

WALLETS_BF = {"orange_money": "Orange Money", "moov": "Moov Money"}
PROVIDERS = {**WALLETS_BF, "stripe": "Carte bancaire (diaspora)", "mock": "Sandbox"}


# ------------------------------------------------------------ prestataires


class CheckoutResult(Protocol):
    status: str  # "pending" | "failed"
    provider_ref: str
    instructions: str  # message FR affiché à l'utilisateur
    checkout_url: str | None


class PaymentGateway(Protocol):
    """Interface d'un prestataire de paiement (agrégateur Mobile Money)."""

    name: str

    async def initiate(
        self, txn: PaymentTransaction, plan: Plan
    ) -> dict:
        """Démarre la transaction. Retourne les clés de CheckoutResult."""

    def verify_webhook(
        self, payload: dict, signature: str | None
    ) -> dict | None:
        """Valide la signature et normalise en
        {txn_ref, event_id, status, reason?} ; None si invalide."""


class MockGateway:
    """Passerelle de CERTIFICATION sandbox — aucun prélèvement réel.

    Le parcours colle au réel : le webhook rejoue les statuts de
    l'agrégateur (succeeded/failed) via les mêmes fonctions d'activation.
    """

    name = "mock"

    async def initiate(self, txn: PaymentTransaction, plan: Plan) -> dict:
        wallet = WALLETS_BF.get(txn.provider, txn.provider)
        return {
            "status": "pending",
            "provider_ref": f"mock-{txn.id}",
            "checkout_url": None,
            "instructions": (
                f"DEMANDE DÉMO : payez {plan.prix_fcfa} FCFA par {wallet} "
                f"pour « {plan.titre} ». Aucun prélèvement réel ne sera "
                "effectué : validez ensuite avec « J'ai payé (démo) »."
            ),
        }

    def verify_webhook(self, payload: dict, signature: str | None) -> dict | None:
        txn_ref = payload.get("txn_ref")
        event_id = payload.get("event_id")
        if not txn_ref or not event_id:
            return None
        status = str(payload.get("status", "")).lower()
        if status not in ("succeeded", "failed", "cancelled"):
            return None
        return {
            "txn_ref": str(txn_ref),
            "event_id": str(event_id),
            "status": status,
            "reason": payload.get("reason"),
        }


class PayDunyaGateway:
    """Agrégateur reconnu en Afrique de l'Ouest (Dakar) — couvre Orange
    Money et Moov Money **Burkina Faso** en wallet `orange-money-ci` /
    `moov-bf`.

    Marche à suivre côté production :
    - créer le compte business → activer Orange Money BF + Moov BF ;
    - provisionner les 4 clés (master/private/public/token) dans le vault ;
    - déclarer l'URL de callback : POST /api/v1/payments/webhook/paydunya
      et activer « payment request » (USSD push wallet Orange Money).

    ⚠️ En l'absence de clés réelles dans ce bac à sable, l'initiation
    réponse 503 explicite. Le squelette HTTP (httpx) est opérationnel :
    vérifié ici statiquement, à brancher au prochain sprint.
    """

    name = "paydunya"
    _BASE = "https://app.paydunya.com"

    def __init__(self) -> None:
        s = get_settings()
        self.master = s.paydunya_master_key
        self.private = s.paydunya_private_key
        self.public = s.paydunya_public_key
        self.token = s.paydunya_token
        self.sandbox = s.paydunya_sandbox

    def _configured(self) -> bool:
        return bool(self.master and self.private and self.public and self.token)

    async def initiate(self, txn: PaymentTransaction, plan: Plan) -> dict:
        if not self._configured():
            raise RuntimeError(
                "PayDunya non configuré (clés manquantes). Basculez sur "
                "PAYMENTS_PROVIDER=mock en attendant le compte business."
            )
        import httpx

        headers = {
            "PAYDUNYA-MASTER-KEY": self.master,
            "PAYDUNYA-PRIVATE-KEY": self.private,
            "PAYDUNYA-PUBLIC-KEY": self.public,
            "PAYDUNYA-TOKEN": self.token,
            "Content-Type": "application/json",
        }
        invoice = {
            "invoice": {
                "items": [
                    {
                        "name": plan.titre,
                        "quantity": 1,
                        "unit_price": str(plan.prix_fcfa),
                        "total_price": str(plan.prix_fcfa),
                        "description": f"Abonnement {plan.titre} FASO LOVE",
                    }
                ],
                "total_amount": plan.prix_fcfa,
                "description": f"FASO LOVE {plan.titre}",
                "callback_url": None,  # webhook déclaré côté tableaux PayDunya
                "cancel_url": None,
                "return_url": None,
            },
            "store": {"name": "FASO LOVE"},
            "custom_data": {"txn_ref": txn.id, "user_id": txn.user_id},
            "actions": {},
        }
        wallet_channel = {
            "orange_money": "orange-money-bf",
            "moov": "moov-bf",
        }.get(txn.provider)
        if wallet_channel is None:
            raise RuntimeError(f"Portefeuille PayDunya inconnu : {txn.provider}")

        async with httpx.AsyncClient(timeout=20) as client:
            cr = await client.post(
                f"{self._BASE}/api/v1/checkout-invoice/create",
                json=invoice,
                headers=headers,
            )
            cr.raise_for_status()
            body = cr.json()
            token = body.get("token")
            # Demande de paiement wallet (USSD push).
            paylr = await client.post(
                f"{self._BASE}/api/v1/checkout-invoice/confirm/{token}"
                if txn.provider != "orange_money"
                else f"{self._BASE}/api/v1/opr/create",
                json=(
                    {"account_alias": txn.phone_e164}
                    if txn.provider != "orange_money"
                    else {
                        # Payment Request Orange : facture + ali téléphone.
                        "account_alias": txn.phone_e164,
                        "invoice_token": token,
                        "channel": wallet_channel,
                    }
                ),
                headers=headers,
            )
            paylr.raise_for_status()
            return {
                "status": "pending",
                "provider_ref": token,
                "checkout_url": body.get("response_text"),
                "instructions": (
                    f"Validez le paiement de {plan.prix_fcfa} FCFA depuis "
                    f"votre compte {WALLETS_BF.get(txn.provider, '')}."
                ),
            }

    def verify_webhook(self, payload: dict, signature: str | None) -> dict | None:
        # PayDunya signe via le header "master-key" renvoyé ; vérification
        # côté contrôleur (signature == master key).
        if not self._configured() or signature != self.master:
            return None
        custom = payload.get("custom_data") or {}
        txn_ref = custom.get("txn_ref")
        event_id = payload.get("token") or payload.get("invoice_token")
        status = (payload.get("status") or "").lower()
        mapping = {"completed": "succeeded", "pending": None, "canceled": "cancelled"}
        if txn_ref is None or event_id is None or mapping.get(status, "") in (None, ""):
            return None
        return {
            "txn_ref": str(txn_ref),
            "event_id": str(event_id),
            "status": mapping[status],
        }


def get_gateway() -> PaymentGateway:
    """Prestataire actif selon la configuration d'environnement."""
    name = get_settings().payments_provider
    if name == "paydunya":
        return PayDunyaGateway()
    return MockGateway()


# ------------------------------------------------------------- services métier

CHECKOUT_IDEMPOTENCY_WINDOW = td(minutes=15)


async def create_checkout(
    db: AsyncSession,
    user: User,
    plan_code: str,
    wallet: str,
    phone_e164: str,
) -> tuple[PaymentTransaction, str]:
    """Crée (ou réutilise une fenêtre 15 min) une transaction en pending.

    Retourne (transaction, instructions FR).
    """
    plan = PLAN_CATALOG[plan_code]
    now = utcnow()

    # Idempotence requête : pas de double demande USSD dans la fenêtre.
    existing = await db.scalar(
        select(PaymentTransaction)
        .where(
            PaymentTransaction.user_id == user.id,
            PaymentTransaction.plan_code == plan_code,
            PaymentTransaction.status.in_(["initiated", "pending"]),
            PaymentTransaction.created_at > now - CHECKOUT_IDEMPOTENCY_WINDOW,
        )
        .order_by(PaymentTransaction.created_at.desc())
        .limit(1)
    )
    if existing is not None:
        return existing, (
            "Demande déjà en cours : vérifiez votre téléphone (menu Mobile "
            "Money) ou patientez quelques minutes."
        )

    txn = PaymentTransaction(
        user_id=user.id,
        provider=wallet,
        plan_code=plan.code,
        amount_fcfa=plan.prix_fcfa,
        phone_e164=phone_e164,
        status="initiated",
    )
    db.add(txn)
    await db.flush()

    gateway = get_gateway()
    try:
        result = await gateway.initiate(txn, plan)
    except Exception:
        # RuntimeError = prestataire non configuré (503 clair côté endpoint) ;
        # autre erreur réseau = message générique. Dans les deux cas, le
        # rollback est assuré par la fermeture de session (GET_DB).
        raise

    txn.status = result["status"]
    txn.provider_ref = result.get("provider_ref")
    txn.checkout_url = result.get("checkout_url")
    await db.commit()
    return txn, result["instructions"]


async def apply_payment_status(
    db: AsyncSession,
    *,
    txn_ref: str,
    event_id: str,
    status: str,
    reason: str | None = None,
) -> tuple[str, PaymentTransaction | None]:
    """Applique un statut confirmé à la transaction (idempotent).

    Retourne ("applied" | "ignored" | "duplicate", transaction).
    """
    # Idempotence GLOBALE : un event_id n'est traité qu'une fois, quel que
    # soit le référent ciblé. Empêche un agrégateur qui réémet un événement
    # posé sur une autre transaction de violer l'unicité (500).
    existing_event = await db.scalar(
        select(PaymentTransaction).where(
            PaymentTransaction.provider_event_id == event_id
        )
    )
    if existing_event is not None:
        return "duplicate", existing_event

    txn = await db.scalar(
        select(PaymentTransaction).where(PaymentTransaction.provider_ref == txn_ref)
    )
    # Le référentiel de référence peut aussi être notre UUID direct (mock).
    if txn is None:
        txn = await db.scalar(
            select(PaymentTransaction).where(PaymentTransaction.id == txn_ref)
        )
    if txn is None:
        return "ignored", None

    if txn.provider_event_id == event_id:
        return "duplicate", txn  # événement déjà traité

    if status != "succeeded":
        if txn.status not in ("succeeded",):
            txn.status = "failed" if status == "failed" else "cancelled"
            txn.failure_reason = reason or "Paiement non abouti."
            txn.provider_event_id = event_id
            await db.commit()
        return "applied", txn

    if txn.status == "succeeded":
        txn.provider_event_id = event_id
        await db.commit()
        return "duplicate", txn

    # Succès confirmé → activation / renouvellement.
    now = utcnow()
    txn.status = "succeeded"
    txn.succeeded_at = now
    txn.provider_event_id = event_id
    txn.updated_at = now

    plan = PLAN_CATALOG[txn.plan_code]
    active = await db.scalar(
        select(Subscription)
        .where(
            Subscription.user_id == txn.user_id,
            Subscription.status == "active",
            Subscription.ends_at > now,
        )
        .order_by(Subscription.ends_at.desc())
        .limit(1)
    )
    if active is not None and active.source_payment_id != txn.id:
        # Renouvellement : empilement sur la fin courante.
        base = max(active.ends_at, now)
        active.ends_at = base + td(days=plan.duree_jours)
        active.plan_code = plan.code
        active.source_payment_id = txn.id
    else:
        db.add(
            Subscription(
                user_id=txn.user_id,
                plan_code=plan.code,
                status="active",
                starts_at=now,
                ends_at=now + td(days=plan.duree_jours),
                source_payment_id=txn.id,
            )
        )
    await db.commit()
    return "applied", txn


# ------------------------------------------------------------------- Quotas


async def get_active_subscription(
    db: AsyncSession, user_id: str
) -> Subscription | None:
    now = utcnow()
    sub = await db.scalar(
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Subscription.ends_at > now,
        )
        .order_by(Subscription.ends_at.desc())
        .limit(1)
    )
    return sub


async def is_premium(db: AsyncSession, user_id: str) -> bool:
    return await get_active_subscription(db, user_id) is not None


def _today_utc_start() -> datetime:
    today = utcnow().date()
    return datetime.combine(today, time.min)


async def count_reactions_today(
    db: AsyncSession, user_id: str, action: str
) -> int:
    return await db.scalar(
        select(func.count())
        .select_from(Like)
        .where(
            Like.from_user_id == user_id,
            Like.action == action,
            Like.created_at >= _today_utc_start(),
        )
    ) or 0


async def quota_snapshot(db: AsyncSession, user_id: str) -> dict:
    """État des quotas du jour pour l'app (GET /subscriptions/me)."""
    settings = get_settings()
    likes = await count_reactions_today(db, user_id, "like")
    supers = await count_reactions_today(db, user_id, "super_like")
    premium = await is_premium(db, user_id)
    return {
        "likes_used": likes,
        "likes_limit": None if premium else settings.free_likes_per_day,
        "super_likes_used": supers,
        "super_likes_limit": None if premium else settings.free_super_likes_per_day,
    }


async def assert_reaction_quota(
    db: AsyncSession, user_id: str, action: str
) -> None:
    """Lève QuotaExceeded(403) si le compte GRATUIT dépasse son quota du jour."""
    if await is_premium(db, user_id):
        return
    settings = get_settings()
    limit = (
        settings.free_super_likes_per_day
        if action == "super_like"
        else settings.free_likes_per_day
    )
    used = await count_reactions_today(db, user_id, action)
    if used >= limit:
        raise QuotaExceeded(action)


class QuotaExceeded(Exception):
    def __init__(self, action: str) -> None:
        self.action = action
        super().__init__(action)
