#!/usr/bin/env python3
"""Lance l'API FASO LOVE en mode développement clé-en-main.

- démarre un PostgreSQL local (via pgserver, données dans `.pgdata/`),
- crée la base si besoin et applique les migrations Alembic,
- expose l'API sur 0.0.0.0:8000 (docs interactives sur /docs).

Envoi SMS en mode console (le code OTP s'affiche dans les logs et le champ
`dev_code` de la réponse, DEV SEULEMENT).

Usage : python3 tools_run_dev_api.py   (prérequis : pip install pgserver)
"""

import asyncio
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PGDATA = os.path.join(BASE_DIR, ".pgdata")

os.chdir(BASE_DIR)
os.environ["DATABASE_URL"] = (
    f"postgresql+asyncpg://postgres@/fasolove?host={PGDATA}"
)
os.environ.setdefault("JWT_SECRET", "dev-preview-secret-0123456789abcdef")
os.environ.setdefault("SMS_PROVIDER", "console")
os.environ.setdefault("OTP_DEV_ECHO", "true")
os.environ.setdefault("CORS_ORIGINS", "*")
# Preview/demo : limites OTP assouplies (parcours répétés depuis la même IP).
os.environ.setdefault("OTP_REQUEST_RATE_LIMIT", "120/minute")
os.environ.setdefault("OTP_VERIFY_RATE_LIMIT", "120/minute")
# Démo : pas de délai anti-renvoi OTP (parcours répétitifs).
os.environ.setdefault("OTP_RESEND_COOLDOWN_SECONDS", "0")


async def ensure_database() -> None:
    import asyncpg

    conn = await asyncpg.connect(host=PGDATA, user="postgres", database="postgres")
    exists = await conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = 'fasolove'"
    )
    if not exists:
        await conn.execute("CREATE DATABASE fasolove")
    await conn.close()


def main() -> None:
    import pgserver

    pgserver.get_server(PGDATA)
    print(f"[dev-api] PostgreSQL local prêt ({PGDATA})")

    asyncio.run(ensure_database())

    from alembic import command
    from alembic.config import Config

    command.upgrade(Config("alembic.ini"), "head")
    print("[dev-api] migrations appliquées")

    if os.environ.get("SEED_DEMO", "1") == "1":
        from tools_seed_demo import seed

        created = asyncio.run(seed())
        print(f"[dev-api] seed démo : {created} nouvelles entités")

        # Les connexions du pool ont été créées dans la boucle du seed ;
        # sans dispose(), uvicorn (autre boucle) hériterait de connexions
        # "attached to a different loop".
        from app.db.session import engine

        asyncio.run(engine.dispose())

    import uvicorn

    print("[dev-api] API FASO LOVE sur http://0.0.0.0:8000 (/docs)")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
