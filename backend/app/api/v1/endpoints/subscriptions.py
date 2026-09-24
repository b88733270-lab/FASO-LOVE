"""Endpoints de monétisation (Phase 7).

Confiance & sécurité :
- le **webhook** est publc mais le payload est VALIDÉ par signature par le
  prestataire agrégateur ; chaque événement est **idempotent** ;
- l'activation Premium n'a lieu qu'après statut `succeeded` CONFIRMÉ ;
- la simulation n'existe qu'en mode sandbox (`payments_simulation_enabled`).
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user, get_db
from app.core.rate_limit import limiter
from app.models.payments import PaymentTransaction
from app.models.user import User
from app.schemas.subscriptions import (
    CheckoutIn,
    CheckoutOut,
    PlanOut,
    PlansOut,
    QuotasOut,
    SimulateOut,
    SubscriptionMeOut,
    TransactionOut,
    WalletOut,
    WebhookAckOut,
)
from app.services.payments import (
    PLAN_CATALOG,
    WALLETS_BF,
    apply_payment_status,
    create_checkout,
    get_active_subscription,
    get_gateway,
    is_premium,
    quota_snapshot,
)
from app.services.auth_service import normalize_bf_phone

router = APIRouter()


@router.get("/subscriptions/plans", response_model=PlansOut)
@limiter.limit("30/minute")
async def list_plans(request: Request) -> PlansOut:
    settings = get_settings()
    wallets = [
        WalletOut(
            provider=p,
            libelle=libelle,
            actif=(settings.payments_provider != "paydunya" and p != "mock")
            or p == "mock",
        )
        for p, libelle in WALLETS_BF.items()
    ]
    if settings.payments_provider == "mock":
        wallets = [
            WalletOut(provider="mock", libelle="Paiement de démonstration", actif=True)
        ]
    return PlansOut(
        plans=[
            PlanOut(
                code=p.code,
                titre=p.titre,
                prix_fcfa=p.prix_fcfa,
                duree_jours=p.duree_jours,
                avantages=list(p.avantages),
            )
            for p in PLAN_CATALOG.values()
        ],
        wallets=wallets,
        gratuit={
            "likes_par_jour": settings.free_likes_per_day,
            "super_likes_par_jour": settings.free_super_likes_per_day,
        },
    )


@router.get("/subscriptions/me", response_model=SubscriptionMeOut)
@limiter.limit("60/minute")
async def my_subscription(
    request: Request,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionMeOut:
    sub = await get_active_subscription(db, me.id)
    quotas = await quota_snapshot(db, me.id)
    return SubscriptionMeOut(
        is_premium=sub is not None,
        plan_code=sub.plan_code if sub else None,
        ends_at=sub.ends_at if sub else None,
        quotas=QuotasOut(**quotas),
    )


@router.post(
    "/subscriptions/checkout",
    response_model=CheckoutOut,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def checkout(
    request: Request,
    body: CheckoutIn,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutOut:
    if body.plan_code not in PLAN_CATALOG:
        raise HTTPException(400, "Offre inconnue.")
    settings = get_settings()
    # En mode réel (paydunya…), le provider « mock » est impensable.
    allowed = (
        {"mock"} if settings.payments_provider == "mock" else set(WALLETS_BF)
    )
    if body.provider not in allowed:
        raise HTTPException(
            400,
            "Moyen de paiement non disponible. Choisissez Orange Money, Moov "
            "Money ou la démonstration (sandbox).",
        )
    try:
        phone = normalize_bf_phone(body.phone_e164 or me.phone_e164)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    try:
        txn, instructions = await create_checkout(
            db, me, body.plan_code, body.provider, phone
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from None
    except Exception:
        raise HTTPException(
            502, "Prestataire de paiement indisponible. Réessayez plus tard."
        ) from None
    return CheckoutOut(
        transaction_id=txn.id,
        status=txn.status,
        instructions=instructions,
        checkout_url=txn.checkout_url,
    )


@router.get("/payments/{txn_id}", response_model=TransactionOut)
@limiter.limit("60/minute")
async def get_transaction(
    request: Request,
    txn_id: str,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentTransaction:
    txn = await db.get(PaymentTransaction, txn_id)
    if txn is None or txn.user_id != me.id:
        raise HTTPException(404, "Transaction introuvable.")
    return txn


@router.post("/payments/{txn_id}/simulate", response_model=SimulateOut)
@limiter.limit("10/minute")
async def simulate_payment(
    request: Request,
    txn_id: str,
    succeed: bool = True,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SimulateOut:
    """DEV/SANDBOX : rejoue la CONFIRMATION du paiement via le chemin webhook
    (même code d'activation, mêmes garanties d'idempotence)."""
    settings = get_settings()
    if not settings.payments_simulation_enabled:
        raise HTTPException(
            404,
            "La simulation de paiement n'est pas disponible sur ce serveur.",
        )
    txn = await db.get(PaymentTransaction, txn_id)
    if txn is None or txn.user_id != me.id:
        raise HTTPException(404, "Transaction introuvable.")
    ref = txn.provider_ref or txn.id
    await apply_payment_status(
        db,
        txn_ref=ref,
        event_id=f"sim-{txn_id}",
        status="succeeded" if succeed else "failed",
        reason="Échec simulé" if not succeed else None,
    )
    return SimulateOut(
        subscription_active=await is_premium(db, me.id)
    )


@router.post("/payments/webhook/{provider}", response_model=WebhookAckOut)
@limiter.limit("240/minute")
async def payments_webhook(
    request: Request,
    provider: str,
    x_master_key: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> WebhookAckOut:
    """Réception des confirmations prestataire (toujours 200 pour stopper
    les rejeux de l'agrégateur ; la sécurité repose sur la signature)."""
    if provider != get_settings().payments_provider:
        return WebhookAckOut(result="ignored")
    try:
        payload = await request.json()
    except Exception:
        return WebhookAckOut(result="ignored")
    if not isinstance(payload, dict):
        return WebhookAckOut(result="ignored")

    gateway = get_gateway()
    event = gateway.verify_webhook(payload, signature=x_master_key)
    if event is None:
        return WebhookAckOut(result="rejected")

    result, _txn = await apply_payment_status(
        db,
        txn_ref=event["txn_ref"],
        event_id=event["event_id"],
        status=event["status"],
        reason=event.get("reason"),
    )
    return WebhookAckOut(result=result)
