"""Tests sécurité/compte : blocages, signalements, admin, suppression/export."""

from app.core.config import get_settings
from app.models.user import User

from tests.conftest import make_match, tiny_jpeg


async def _promote_admin(db_session, user_id: str) -> None:
    """Élève un utilisateur au rôle admin (via ORM — pas d'API publique)."""
    user = await db_session.get(User, user_id)
    user.role = "admin"
    await db_session.commit()


async def test_signalement_cycle_complet(make_user, client, db_session):
    id_victime, _, h_victime = await make_user(
        display_name="Victime", gender="female"
    )
    id_arbitraire, _, h_arbitraire = await make_user(
        display_name="Arnaqueur", gender="male"
    )
    id_admin, _, h_admin = await make_user(
        display_name="Modo", gender="female", age=35
    )
    await _promote_admin(db_session, id_admin)

    # Un non-admin ne voit pas le back-office.
    r = await client.get("/api/v1/admin/reports", headers=h_victime)
    assert r.status_code == 403

    # Signalement arnaque (motif métier) → file admin.
    r = await client.post(
        "/api/v1/reports",
        json={
            "reported_user_id": id_arbitraire,
            "reason": "scam",
            "details": "Il demande de l'argent en avance.",
        },
        headers=h_victime,
    )
    assert r.status_code == 201
    report_id = r.json()["id"]
    assert "Merci" in r.json()["message"]

    r = await client.get("/api/v1/admin/reports", headers=h_admin)
    pending = r.json()
    assert any(p["id"] == report_id and p["reason"] == "scam" for p in pending)
    assert any(p["reported_name"] == "Arnaqueur" for p in pending)

    # Résolution.
    r = await client.post(
        f"/api/v1/admin/reports/{report_id}/resolve",
        json={"resolution": "resolved"},
        headers=h_admin,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"

    # Motif invalide → 400.
    r = await client.post(
        "/api/v1/reports",
        json={"reported_user_id": id_arbitraire, "reason": "invente"},
        headers=h_victime,
    )
    assert r.status_code == 400


async def test_admin_stats_et_gestion_utilisateurs(make_user, client, db_session):
    id_u1, _, h_u1 = await make_user(display_name="StatF", gender="female")
    id_u2, _, h_u2 = await make_user(display_name="StatH", gender="male")
    match_id = await make_match(client, h_u1, h_u2, id_u1, id_u2)
    id_admin, _, h_admin = await make_user(display_name="Boss", gender="male", age=40)
    await _promote_admin(db_session, id_admin)

    r = await client.get("/api/v1/admin/stats", headers=h_admin)
    assert r.status_code == 200
    stats = r.json()
    assert stats["users_total"] >= 3
    assert stats["users_verified"] >= 3
    assert stats["matches_total"] >= 1
    assert stats["profiles_with_photo"] >= 2

    # Recherche utilisateur + désactivation → compte coupé immédiatement.
    r = await client.get("/api/v1/admin/users?q=StatH", headers=h_admin)
    assert any(u["display_name"] == "StatH" for u in r.json())

    r = await client.patch(
        f"/api/v1/admin/users/{id_u2}",
        json={"is_active": False},
        headers=h_admin,
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    # Le compte désactivé n'a plus accès à l'API (jeton encore valide → 401).
    r = await client.get("/api/v1/auth/me", headers=h_u2)
    assert r.status_code == 401


async def test_moderation_photo_pending(make_user, client, db_session):
    settings = get_settings()
    original = settings.media_auto_approve
    settings.media_auto_approve = False  # mode production : validation requise
    try:
        id_admin, _, h_admin = await make_user(display_name="ModoPhotos", gender="female", age=33)
        await _promote_admin(db_session, id_admin)
        id_u, _, h_u = await make_user(display_name="PhotoUser", gender="male")
        me = (await client.get("/api/v1/profiles/me", headers=h_u)).json()
        photo_id = me["photos"][0]["id"]
        assert me["photos"][0]["status"] == "pending"

        # Tant qu'elle est en attente, l'utilisateur n'apparaît pas en découverte.
        _, _, h_autre = await make_user(display_name="Autre", gender="female")
        r = await client.get("/api/v1/discover", headers=h_autre)
        assert id_u not in [c["user_id"] for c in r.json()]

        # File admin → approbation → visible.
        r = await client.get("/api/v1/admin/photos", headers=h_admin)
        assert any(p["id"] == photo_id for p in r.json())
        r = await client.post(
            f"/api/v1/admin/photos/{photo_id}/moderate",
            json={"action": "approve"},
            headers=h_admin,
        )
        assert r.json()["status"] == "approved"
        r = await client.get("/api/v1/discover", headers=h_autre)
        assert id_u in [c["user_id"] for c in r.json()]
    finally:
        settings.media_auto_approve = original


async def test_suppression_compte_efface_tout(make_user, client):
    id_a, _, h_a = await make_user(display_name="Partante", gender="female")
    id_b, _, h_b = await make_user(display_name="Restant", gender="male")
    match_id = await make_match(client, h_a, h_b, id_a, id_b)
    await client.post(
        f"/api/v1/matches/{match_id}/messages",
        json={"content": "message avant suppression"},
        headers=h_a,
    )

    # Export (portabilité) avant suppression.
    r = await client.get("/api/v1/users/me/export", headers=h_a)
    assert r.status_code == 200
    assert r.json()["compte"]["telephone"].startswith("+226")
    assert r.json()["messages_envoyes"]

    # Suppression → 204 ; le jeton ne vaut plus rien.
    r = await client.delete("/api/v1/users/me", headers=h_a)
    assert r.status_code == 204
    r = await client.get("/api/v1/auth/me", headers=h_a)
    assert r.status_code == 401

    # Le correspondant ne voit plus ni le match ni la personne.
    matches = (await client.get("/api/v1/matches", headers=h_b)).json()
    assert all(m["match_id"] != match_id for m in matches)
    r = await client.get(f"/api/v1/profiles/{id_a}", headers=h_b)
    assert r.status_code == 404


async def test_blocage_cycle(make_user, client):
    id_a, _, h_a = await make_user(display_name="Bloquante", gender="female")
    id_b, _, h_b = await make_user(display_name="Bloque", gender="male")

    # Signalement puis blocage ; idempotence du blocage.
    for _ in range(2):
        r = await client.post(
            "/api/v1/blocks", json={"user_id": id_b}, headers=h_a
        )
        assert r.status_code in (200, 201)

    r = await client.get("/api/v1/blocks", headers=h_a)
    assert [b["user_id"] for b in r.json()] == [id_b]

    # Le profil bloqué devient introuvable pour elle.
    r = await client.get(f"/api/v1/profiles/{id_b}", headers=h_a)
    assert r.status_code == 404

    # Déblocage → profil visible à nouveau.
    r = await client.delete(f"/api/v1/blocks/{id_b}", headers=h_a)
    assert r.status_code == 204
    r = await client.get(f"/api/v1/profiles/{id_b}", headers=h_a)
    assert r.status_code == 200
