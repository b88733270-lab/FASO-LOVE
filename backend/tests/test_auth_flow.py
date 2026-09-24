"""Tests du flux d'authentification complet (endpoints)."""

from datetime import date, timedelta

PHONE = "+22670112233"
PHONE_2 = "65098877"  # format local, sans indicatif

ADULT_DATE = "1998-05-12"


def underage_date() -> str:
    """Il y a 17 ans et 1 jour → systématiquement mineur (règle 18+)."""
    d = date.today() - timedelta(days=17 * 365 + 6)
    return d.isoformat()


async def request_code(client, phone: str) -> str:
    r = await client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert r.status_code == 200, r.text
    assert r.json()["message"].startswith("Code de vérification")
    return r.json()["dev_code"]


async def test_health(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["app"] == "FASO LOVE API"


async def test_creation_compte_puis_reconnexion(client):
    # 1) Demande de code (format local accepté et normalisé).
    code = await request_code(client, PHONE_2)

    # 2) Nouveau numéro sans date de naissance → 400 explicite ; le code
    #    n'est PAS consommé (pas de SMS gaspillé).
    r = await client.post(
        "/api/v1/auth/otp/verify", json={"phone": PHONE_2, "code": code}
    )
    assert r.status_code == 400
    assert "date de naissance" in r.json()["detail"]

    # 3) Avec la date de naissance adulte → compte créé + jetons.
    r = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": PHONE_2, "code": code, "birthdate": ADULT_DATE},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_new_user"] is True
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]
    assert body["expires_in"] > 0

    # 4) Le code est à usage unique : réutilisation refusée.
    r = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": PHONE_2, "code": code, "birthdate": ADULT_DATE},
    )
    assert r.status_code == 401

    # 5) Reconnexion (compte existant, pas besoin de la naissance).
    code2 = await request_code(client, PHONE_2)
    r = await client.post(
        "/api/v1/auth/otp/verify", json={"phone": PHONE_2, "code": code2}
    )
    assert r.status_code == 200
    assert r.json()["is_new_user"] is False


async def test_mineur_refuse_18_plus(client):
    code = await request_code(client, PHONE)
    r = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": PHONE, "code": code, "birthdate": underage_date()},
    )
    assert r.status_code == 403
    assert "18" in r.json()["detail"]


async def test_code_incorrect(client):
    await request_code(client, PHONE)
    r = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": PHONE, "code": "000000"},
    )
    assert r.status_code == 401
    assert "incorrect" in r.json()["detail"]


async def test_numero_invalide(client):
    r = await client.post("/api/v1/auth/otp/request", json={"phone": "12345"})
    assert r.status_code == 400
    r = await client.post(
        "/api/v1/auth/otp/request", json={"phone": "+22620112233"}  # fixe
    )
    assert r.status_code == 400


async def test_me(client):
    code = await request_code(client, PHONE)
    tokens = (
        await client.post(
            "/api/v1/auth/otp/verify",
            json={"phone": PHONE, "code": code, "birthdate": ADULT_DATE},
        )
    ).json()

    # Sans jeton → 401.
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401

    # Avec l'access token → informations du compte.
    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 200
    me = r.json()
    assert me["phone_e164"] == PHONE
    assert me["age"] >= 18
    assert me["is_verified"] is True
    assert me["role"] == "user"


async def test_rotation_refresh_token(client):
    code = await request_code(client, PHONE)
    tokens = (
        await client.post(
            "/api/v1/auth/otp/verify",
            json={"phone": PHONE, "code": code, "birthdate": ADULT_DATE},
        )
    ).json()

    # Rotation : nouveau couple de jetons, l'ancien refresh est révoqué.
    r = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert r.status_code == 200
    rotated = r.json()
    assert rotated["refresh_token"] != tokens["refresh_token"]

    # Réutilisation de l'ancien refresh token → refusée (détection).
    r = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert r.status_code == 401

    # Le nouveau fonctionne.
    r = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]}
    )
    assert r.status_code == 200


async def test_logout_revoque(client):
    code = await request_code(client, PHONE)
    tokens = (
        await client.post(
            "/api/v1/auth/otp/verify",
            json={"phone": PHONE, "code": code, "birthdate": ADULT_DATE},
        )
    ).json()

    r = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert r.status_code == 204

    r = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert r.status_code == 401

    # Déconnexion idempotente : un jeton déjà invalide ne plante pas.
    r = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert r.status_code == 204
