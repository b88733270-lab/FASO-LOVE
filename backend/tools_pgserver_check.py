#!/usr/bin/env python3
"""Vérification E2E de l'API sur un **vrai PostgreSQL** (utilitaire local).

Utilise `pgserver` (binaires PostgreSQL précompilés, aucune installation
système requise — pratique dans les environnements sans droits root) :

    pip install pgserver
    python3 tools_pgserver_check.py

Séquence : démarre PostgreSQL (données dans .pgdata/), crée la base,
applique les migrations Alembic, puis exécute le flux OTP complet
(demande → vérification 18+ → /me → rotation du refresh token).
"""

import asyncio
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PGDATA = os.path.join(BASE_DIR, ".pgdata")

os.chdir(BASE_DIR)
os.environ["DATABASE_URL"] = (
    f"postgresql+asyncpg://postgres@/fasolove?host={PGDATA}"
)
os.environ.setdefault("JWT_SECRET", "e2e-check-secret-0123456789")
os.environ.setdefault("OTP_DEV_ECHO", "true")
os.environ.setdefault("OTP_RESEND_COOLDOWN_SECONDS", "0")

import pgserver  # noqa: E402

PHONE = "+22670112233"
BIRTHDATE = "1995-02-14"


async def ensure_database() -> None:
    import asyncpg

    conn = await asyncpg.connect(host=PGDATA, user="postgres", database="postgres")
    exists = await conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = 'fasolove'"
    )
    if not exists:
        await conn.execute("CREATE DATABASE fasolove")
        print("→ base 'fasolove' créée")
    await conn.close()


async def e2e() -> None:
    from httpx import ASGITransport, AsyncClient

    from app.main import create_app

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://e2e"
    ) as c:
        r = await c.get("/api/v1/health")
        assert r.status_code == 200, r.text
        print("✅ /health sur PostgreSQL :", r.json()["status"])

        r = await c.post("/api/v1/auth/otp/request", json={"phone": PHONE})
        assert r.status_code == 200, r.text
        code = r.json()["dev_code"]
        print("✅ OTP demandé (console) :", code)

        r = await c.post(
            "/api/v1/auth/otp/verify",
            json={"phone": PHONE, "code": code, "birthdate": BIRTHDATE},
        )
        assert r.status_code == 200, r.text
        tokens = r.json()
        assert tokens["is_new_user"] is True
        print("✅ Compte 18+ créé, jetons émis")

        r = await c.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert r.status_code == 200, r.text
        print("✅ /me :", r.json()["phone_e164"], "— âge", r.json()["age"])

        r = await c.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert r.status_code == 200, r.text
        print("✅ Rotation du refresh token")

        r = await c.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert r.status_code == 401, r.text
        print("✅ Réutilisation de l'ancien refresh token refusée (401)")


def main() -> int:
    print(f"→ PostgreSQL local (pgserver) : {PGDATA}")
    pgserver.get_server(PGDATA)
    asyncio.run(ensure_database())

    from alembic import command
    from alembic.config import Config

    command.upgrade(Config("alembic.ini"), "head")
    print("→ migrations Alembic appliquées sur PostgreSQL")

    asyncio.run(e2e())
    print("\n🎉 E2E POSTGRESQL : tout est fonctionnel.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
