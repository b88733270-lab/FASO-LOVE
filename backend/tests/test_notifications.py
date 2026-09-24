"""Tests Phase 8 — notifications : appareils push (idempotence), cloche
in-app alimentée par les événements métier (match, message), badge de
non-lues, anti-spam par conversation, préférences utilisateur, RGPD."""

from sqlalchemy import select

from app.models.notifications import Notification, PushDevice
from tests.conftest import make_match


async def _promote_admin(db_session, user_id: str) -> None:
    """Élève un utilisateur au rôle admin (via ORM — pas d'API publique)."""
    from app.models.user import User

    user = await db_session.get(User, user_id)
    user.role = "admin"
    await db_session.commit()


async def test_enregistrement_appareil_idempotent(make_user, client):
    _, _, h = await make_user(display_name="Clotilde", gender="female")

    r = await client.post(
        "/api/v1/devices",
        json={"platform": "android", "token": "fcm-token-aaa-0000001"},
        headers=h,
    )
    assert r.status_code == 201
    device_id = r.json()["id"]
    assert r.json()["platform"] == "android"

    # Même token re-joué par l'app au démarrage → même appareil (pas de doublon).
    r2 = await client.post(
        "/api/v1/devices",
        json={"platform": "android", "token": "fcm-token-aaa-0000001"},
        headers=h,
    )
    assert r2.status_code == 201
    assert r2.json()["id"] == device_id

    # Mauvaise plateforme → 422.
    r = await client.post(
        "/api/v1/devices", json={"platform": "amiga", "token": "tok-123456789"}, headers=h
    )
    assert r.status_code == 422


async def test_appareil_reattribution_et_desenregistrement(make_user, client):
    """Le même token FCM peut passer d'un utilisateur à un autre (en
    déconnexion/reconnexion sur le même téléphone) → ré-attribution, et la
    suppression d'un compte ne laisse aucun appareil fantôme."""
    id_a, _, h_a = await make_user(display_name="Ange", gender="female")
    id_b, _, h_b = await make_user(display_name="Bruno", gender="male")

    tok = "fcm-token-shared-00000007"
    await client.post(
        "/api/v1/devices", json={"platform": "android", "token": tok}, headers=h_a
    )
    # Changement de compte sur la même machine → le token suit.
    await client.post(
        "/api/v1/devices", json={"platform": "android", "token": tok}, headers=h_b
    )

    # A ne peut plus désinscrire un token qui ne lui appartient plus.
    r = await client.delete(f"/api/v1/devices/{tok}", headers=h_a)
    assert r.status_code == 404
    # B, propriétaire actuel, le retire proprement (déconnexion de l'app).
    r = await client.delete(f"/api/v1/devices/{tok}", headers=h_b)
    assert r.status_code == 204


async def test_match_notifie_les_deux_membres(make_user, client):
    id_a, _, h_a = await make_user(display_name="Claire", gender="female")
    id_b, _, h_b = await make_user(display_name="Drissa", gender="male")

    match_id = await make_match(client, h_a, h_b, id_a, id_b)

    # Les deux ont reçu la cloche "Nouveau match 🎉" avec un payload routable.
    for headers, autre in ((h_a, "Drissa"), (h_b, "Claire")):
        r = await client.get("/api/v1/notifications", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["unread_count"] >= 1
        notif = next(n for n in data["items"] if n["kind"] == "match")
        assert notif["payload"]["match_id"] == match_id
        assert notif["payload"]["peer_name"] == autre
        assert "🎉" in notif["title"]


async def test_message_notifie_destinataire_avec_anti_spam(make_user, client):
    id_a, _, h_a = await make_user(display_name="Emma", gender="female")
    id_b, _, h_b = await make_user(display_name="Faisal", gender="male")
    match_id = await make_match(client, h_a, h_b, id_a, id_b)

    # B envoie deux messages d'affilée → UNE SEULE notification empilée.
    for message in ("Salut Emma !", "Tu es de Ouaga ?"):
        r = await client.post(
            f"/api/v1/matches/{match_id}/messages",
            json={"content": message},
            headers=h_b,
        )
        assert r.status_code == 201

    r = await client.get("/api/v1/notifications", headers=h_a)
    data = r.json()
    notifs_msg = [n for n in data["items"] if n["kind"] == "message"]
    assert len(notifs_msg) == 1
    assert notifs_msg[0]["payload"]["peer_name"] == "Faisal"
    # Emma, EXPÉDITEUR fantôme ? Non : l'expéditeur n'est jamais notifié.
    r = await client.get("/api/v1/notifications", headers=h_b)
    notifs_msg_b = [n for n in r.json()["items"] if n["kind"] == "message"]
    assert notifs_msg_b == []
    # Badge : match + message = 2 non-lues côté Emma.
    assert data["unread_count"] == 2


async def test_badge_lecture_unitaire_et_globale(make_user, client):
    id_a, _, h_a = await make_user(display_name="Gifty", gender="female")
    id_b, _, h_b = await make_user(display_name="Hassane", gender="male")
    match_id = await make_match(client, h_a, h_b, id_a, id_b)

    r = await client.get("/api/v1/notifications/count", headers=h_a)
    assert r.json()["unread_count"] == 1

    r = await client.get("/api/v1/notifications", headers=h_a)
    notif_id = r.json()["items"][0]["id"]
    r = await client.post(f"/api/v1/notifications/{notif_id}/read", headers=h_a)
    assert r.status_code == 200 and r.json()["read"] is True
    # Idempotent : marquer une entrée déjà lue ne casse rien.
    r = await client.post(f"/api/v1/notifications/{notif_id}/read", headers=h_a)
    assert r.status_code == 200

    # Propriété : une notification d'A n'est jamais lisible par B.
    r = await client.post(f"/api/v1/notifications/{notif_id}/read", headers=h_b)
    assert r.status_code == 404

    # Nouvel événement → nouveau badge, puis lecture globale efficace.
    r = await client.get("/api/v1/notifications/count", headers=h_a)
    assert r.json()["unread_count"] == 0
    await client.post(
        f"/api/v1/matches/{match_id}/messages",
        json={"content": "Nouveau coucou !"},
        headers=h_b,
    )
    r = await client.get("/api/v1/notifications/count", headers=h_a)
    assert r.json()["unread_count"] == 1
    r = await client.post("/api/v1/notifications/read-all", headers=h_a)
    assert r.json()["updated"] == 1
    r = await client.get("/api/v1/notifications/count", headers=h_a)
    assert r.json()["unread_count"] == 0


async def test_preferences_bloquent_le_canal(make_user, client):
    id_a, _, h_a = await make_user(display_name="Isabelle", gender="female")
    id_b, _, h_b = await make_user(display_name="Jules", gender="male")

    # Isabelle coupe TOUTES les notifications de match.
    r = await client.put(
        "/api/v1/notifications/prefs",
        json={"matches": False, "messages": True},
        headers=h_a,
    )
    assert r.status_code == 200 and r.json()["matches"] is False
    r = await client.get("/api/v1/notifications/prefs", headers=h_a)
    assert r.json() == {"matches": False, "messages": True}

    await make_match(client, h_a, h_b, id_a, id_b)

    # Aucun badge côté Isabelle, Jules est lui bien notifié.
    r = await client.get("/api/v1/notifications/count", headers=h_a)
    assert r.json()["unread_count"] == 0
    r = await client.get("/api/v1/notifications/count", headers=h_b)
    assert r.json()["unread_count"] == 1


async def test_suppression_compte_efface_notifications_et_appareils(
    make_user, client, db_session
):
    id_a, _, h_a = await make_user(display_name="Kadia", gender="female")
    id_b, _, h_b = await make_user(display_name="Lassina", gender="male")

    await client.post(
        "/api/v1/devices",
        json={"platform": "ios", "token": "fcm-token-kadia-00000002"},
        headers=h_a,
    )
    match_id = await make_match(client, h_a, h_b, id_a, id_b)
    await client.post(
        f"/api/v1/matches/{match_id}/messages",
        json={"content": "On s'appelle ?"},
        headers=h_b,
    )

    # Export RGPD : la cloche est présente côté A.
    r = await client.get("/api/v1/users/me/export", headers=h_a)
    assert r.status_code == 200
    notif_export = r.json().get("notifications", [])
    assert len(notif_export) >= 2  # match + message

    # Suppression complète : notifications ET appareils partent.
    r = await client.delete("/api/v1/users/me", headers=h_a)
    assert r.status_code == 204
    restants = (
        await db_session.scalars(
            select(Notification).where(Notification.user_id == id_a)
        )
    ).all()
    appareils = (
        await db_session.scalars(
            select(PushDevice).where(PushDevice.user_id == id_a)
        )
    ).all()
    assert restants == []
    assert appareils == []


async def test_admin_stats_comptent_les_notifications(make_user, client, db_session):
    """Le tableau de bord admin expose les volumes clubs+appareils push."""
    id_admin, _, h_admin = await make_user(display_name="Mgr")
    await _promote_admin(db_session, id_admin)

    _, _, h_a = await make_user(display_name="Nadine", gender="female")
    await client.post(
        "/api/v1/devices",
        json={"platform": "web", "token": "fcm-token-web-000000003"},
        headers=h_a,
    )

    r = await client.get("/api/v1/admin/stats", headers=h_admin)
    assert r.status_code == 200
    data = r.json()
    assert data["notifications_total"] >= 0
    assert data["push_devices_total"] >= 1
