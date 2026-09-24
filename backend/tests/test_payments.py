"""Tests Phase 7 — monétisation : offres, quotas freemium, checkout
idempotent, activation Premium via webhook/simulation, rejouabilité, RGPD."""

from datetime import timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import utcnow
from app.models.payments import PaymentTransaction, Subscription


def _settings_restore(settings, **saved):
    for k, v in saved.items():
        setattr(settings, k, v)


async def test_catalogue_offres_et_wallets(client):
    r = await client.get("/api/v1/subscriptions/plans")
    assert r.status_code == 200
    data = r.json()
    codes = [p["code"] for p in data["plans"]]
    assert codes == ["premium_week", "premium_month", "premium_3m"]
    prix = {p["code"]: p["prix_fcfa"] for p in data["plans"]}
    assert prix == {"premium_week": 1500, "premium_month": 3500, "premium_3m": 9000}
    # En sandbox : seul le portefeuille de démonstration est actif.
    assert data["wallets"] == [
        {"provider": "mock", "libelle": "Paiement de démonstration", "actif": True}
    ]
    assert data["gratuit"]["likes_par_jour"] == 30


async def test_checkout_idempotent_activation_et_quotas_ilimites(
    make_user, client, db_session
):
    _, _, h_a = await make_user(display_name="Acheteuse", gender="female")
    id_b, _, _ = await make_user(display_name="Cible", gender="male")

    corps = {"plan_code": "premium_month", "provider": "mock"}
    r1 = await client.post("/api/v1/subscriptions/checkout", json=corps, headers=h_a)
    assert r1.status_code == 201
    txn_id = r1.json()["transaction_id"]
    assert r1.json()["status"] == "pending"
    assert "FCFA" in r1.json()["instructions"]

    # Rejeu immédiat → même transaction (idempotence requête 15 min).
    r2 = await client.post("/api/v1/subscriptions/checkout", json=corps, headers=h_a)
    assert r2.json()["transaction_id"] == txn_id

    # Avant paiement confirmé : toujours gratuité.
    me = await client.get("/api/v1/subscriptions/me", headers=h_a)
    assert me.json()["is_premium"] is False

    # Simulation de confirmation (sandbox) → activation.
    r = await client.post(f"/api/v1/payments/{txn_id}/simulate", headers=h_a)
    assert r.status_code == 200 and r.json()["subscription_active"] is True

    me = await client.get("/api/v1/subscriptions/me", headers=h_a)
    assert me.json()["is_premium"] is True
    assert me.json()["plan_code"] == "premium_month"
    assert me.json()["quotas"]["likes_limit"] is None  # illimité

    # Un abonnement actif existe en base, rattaché à la transaction.
    sub = (
        (
            await db_session.execute(
                select(Subscription).where(Subscription.source_payment_id == txn_id)
            )
        )
        .scalars()
        .first()
    )
    assert sub is not None and sub.status == "active"

    # Le premium peut liker sans quota même avec quota 0 configuré.
    settings = get_settings()
    saved = {"free_likes_per_day": settings.free_likes_per_day}
    settings.free_likes_per_day = 0  # un compte gratuit ne pourrait rien faire
    try:
        r = await client.post(
            "/api/v1/discover/react",
            json={"target_user_id": id_b, "action": "like"},
            headers=h_a,
        )
        assert r.status_code == 200  # Premium = illimité
    finally:
        _settings_restore(settings, **saved)


async def test_quota_freemium_bloque_le_gratuit(make_user, client):
    settings = get_settings()
    saved = {"free_likes_per_day": settings.free_likes_per_day}
    settings.free_likes_per_day = 2
    try:
        _, _, h_a = await make_user(display_name="Gratuite", gender="female")
        cibles = []
        for i in range(3):
            id_c, _, _ = await make_user(display_name=f"Cible{i}", gender="male")
            cibles.append(id_c)

        # 2 likes gratuits autorisés par jour.
        for id_c in cibles[:2]:
            r = await client.post(
                "/api/v1/discover/react",
                json={"target_user_id": id_c, "action": "like"},
                headers=h_a,
            )
            assert r.status_code == 200

        # 3e like → blocage 403 FR orienté Premium.
        r = await client.post(
            "/api/v1/discover/react",
            json={"target_user_id": cibles[2], "action": "like"},
            headers=h_a,
        )
        assert r.status_code == 403
        assert "Premium" in r.json()["detail"]
    finally:
        _settings_restore(settings, **saved)


async def test_quotas_super_like_distincts(make_user, client):
    settings = get_settings()
    saved = {"free_super_likes_per_day": settings.free_super_likes_per_day}
    settings.free_super_likes_per_day = 1
    try:
        _, _, h_a = await make_user(display_name="Superlike", gender="female")
        id1, _, _ = await make_user(display_name="S1", gender="male")
        id2, _, _ = await make_user(display_name="S2", gender="male")
        r = await client.post(
            "/api/v1/discover/react",
            json={"target_user_id": id1, "action": "super_like"},
            headers=h_a,
        )
        assert r.status_code == 200
        r = await client.post(
            "/api/v1/discover/react",
            json={"target_user_id": id2, "action": "super_like"},
            headers=h_a,
        )
        assert r.status_code == 403
        # …mais le like ordinaire reste ouvert.
        r = await client.post(
            "/api/v1/discover/react",
            json={"target_user_id": id2, "action": "like"},
            headers=h_a,
        )
        assert r.status_code == 200
    finally:
        _settings_restore(settings, **saved)


async def test_webhook_idempotent_et_rejeu(make_user, client, db_session):
    _, _, h_a = await make_user(display_name="Webhoockee", gender="female")
    r = await client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan_code": "premium_week", "provider": "mock"},
        headers=h_a,
    )
    txn_id = r.json()["transaction_id"]
    txn = await db_session.get(PaymentTransaction, txn_id)
    ref = txn.provider_ref

    # 1re notification → activation.
    r = await client.post(
        "/api/v1/payments/webhook/mock",
        json={"txn_ref": ref, "event_id": "evt-1", "status": "succeeded"},
    )
    assert r.status_code == 200 and r.json()["result"] == "applied"
    me = await client.get("/api/v1/subscriptions/me", headers=h_a)
    assert me.json()["is_premium"] is True
    fin_initiale = me.json()["ends_at"]

    # Rejeu du MÊME événement (comportement classique d'agrégateur) → doublon refusé.
    r = await client.post(
        "/api/v1/payments/webhook/mock",
        json={"txn_ref": ref, "event_id": "evt-1", "status": "succeeded"},
    )
    assert r.json()["result"] == "duplicate"
    me2 = await client.get("/api/v1/subscriptions/me", headers=h_a)
    assert me2.json()["ends_at"] == fin_initiale  # pas de double ajout de durée

    # Événement DIFFÉRENT mais transaction déjà soldée → refusé aussi.
    r = await client.post(
        "/api/v1/payments/webhook/mock",
        json={"txn_ref": ref, "event_id": "evt-2", "status": "succeeded"},
    )
    assert r.json()["result"] == "duplicate"
    me3 = await client.get("/api/v1/subscriptions/me", headers=h_a)
    assert me3.json()["ends_at"] == fin_initiale

    # Webhook de mauvais fournisseur → ignoré.
    r = await client.post("/api/v1/payments/webhook/paydunya", json={})
    assert r.json()["result"] == "ignored"

    # Transaction inconnue → ignorée sans erreur (arrête les rejeux).
    r = await client.post(
        "/api/v1/payments/webhook/mock",
        json={"txn_ref": "inexistant", "event_id": "evt-9", "status": "succeeded"},
    )
    assert r.json()["result"] == "ignored"


async def test_echec_simule_et_renouvellement_empile(make_user, client, db_session):
    _, _, h_a = await make_user(display_name="EchecEtRenouille", gender="female")

    # Échec simulé : transaction failed, jamais premium.
    r = await client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan_code": "premium_week", "provider": "mock"},
        headers=h_a,
    )
    txn_id = r.json()["transaction_id"]
    r = await client.post(
        f"/api/v1/payments/{txn_id}/simulate?succeed=false", headers=h_a
    )
    assert r.json()["subscription_active"] is False
    r2 = await client.get(f"/api/v1/payments/{txn_id}", headers=h_a)
    assert r2.json()["status"] == "failed"

    # Achat réussi puis second achat → cumul de durée (renouvellement).
    r = await client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan_code": "premium_week", "provider": "mock"},
        headers=h_a,
    )
    t1 = r.json()["transaction_id"]
    await client.post(f"/api/v1/payments/{t1}/simulate", headers=h_a)
    me1 = (await client.get("/api/v1/subscriptions/me", headers=h_a)).json()
    assert me1["is_premium"] is True

    r = await client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan_code": "premium_week", "provider": "mock"},
        headers=h_a,
    )
    t2 = r.json()["transaction_id"]
    assert t2 != t1
    await client.post(f"/api/v1/payments/{t2}/simulate", headers=h_a)
    me2 = (await client.get("/api/v1/subscriptions/me", headers=h_a)).json()
    fins = {
        me1["ends_at"]: "fin1",
        me2["ends_at"]: "fin2",
    }
    assert me2["ends_at"] > me1["ends_at"], f"empilement KO: {fins}"


async def test_simulation_desactivee_hors_sandbox(make_user, client):
    settings = get_settings()
    saved = {"payments_simulation_enabled": settings.payments_simulation_enabled}
    settings.payments_simulation_enabled = False
    try:
        _, _, h_a = await make_user(display_name="Prod", gender="female")
        r = await client.post(
            "/api/v1/subscriptions/checkout",
            json={"plan_code": "premium_week", "provider": "mock"},
            headers=h_a,
        )
        txn_id = r.json()["transaction_id"]
        r = await client.post(f"/api/v1/payments/{txn_id}/simulate", headers=h_a)
        assert r.status_code == 404
    finally:
        _settings_restore(settings, **saved)


async def test_numero_portefeuille_personnalise_normalise(
    make_user, client, db_session
):
    _, _, h_a = await make_user(display_name="Wallet", gender="female")
    r = await client.post(
        "/api/v1/subscriptions/checkout",
        json={
            "plan_code": "premium_week",
            "provider": "mock",
            "phone_e164": "70 12 34 56",
        },
        headers=h_a,
    )
    assert r.status_code == 201
    txn = await db_session.get(
        PaymentTransaction, r.json()["transaction_id"]
    )
    assert txn.phone_e164 == "+22670123456"


async def test_expiration_abonnement(make_user, client, db_session):
    _, _, h_a = await make_user(display_name="Expire", gender="female")
    me = await client.get("/api/v1/auth/me", headers=h_a)
    user_id = me.json()["id"]

    sub = Subscription(
        user_id=user_id,
        plan_code="premium_week",
        status="active",
        starts_at=utcnow() - timedelta(days=10),
        ends_at=utcnow() - timedelta(days=3),  # expiré
    )
    db_session.add(sub)
    await db_session.commit()

    me = await client.get("/api/v1/subscriptions/me", headers=h_a)
    assert me.json()["is_premium"] is False


async def test_suppression_compte_efface_monetisation(make_user, client, db_session):
    id_a, _, h_a = await make_user(display_name="AcheteuseSupp", gender="female")

    # Achat confirmé.
    r = await client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan_code": "premium_month", "provider": "mock"},
        headers=h_a,
    )
    await client.post(
        f"/api/v1/payments/{r.json()['transaction_id']}/simulate", headers=h_a
    )
    assert (
        (await client.get("/api/v1/subscriptions/me", headers=h_a)).json()["is_premium"]
        is True
    )

    # Export inclut abonnement + transaction (portabilité).
    export = (await client.get("/api/v1/users/me/export", headers=h_a)).json()
    assert export["abonnements"] and export["transactions"]
    assert export["transactions"][0]["montant_fcfa"] == 3500

    # Suppression → tout effacé (y compris abonnement + transactions).
    r = await client.delete("/api/v1/users/me", headers=h_a)
    assert r.status_code == 204
    subs = (
        (
            await db_session.execute(
                select(Subscription).where(
                    Subscription.user_id == id_a
                )
            )
        )
        .scalars()
        .all()
    )
    txns = (
        (
            await db_session.execute(
                select(PaymentTransaction).where(
                    PaymentTransaction.user_id == id_a
                )
            )
        )
        .scalars()
        .all()
    )
    assert subs == [] and txns == []
