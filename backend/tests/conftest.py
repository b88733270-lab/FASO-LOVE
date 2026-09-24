"""Configuration pytest : environnement de test isolé (SQLite en mémoire).

Les variables d'environnement sont posées AVANT tout import applicatif
(les Settings sont mises en cache au premier accès).
"""

import os

os.environ.setdefault("ENV", "test")
os.environ.setdefault("JWT_SECRET", "secret-de-test-pytest-0123456789abcdef")
os.environ.setdefault("OTP_DEV_ECHO", "true")
os.environ.setdefault("OTP_RESEND_COOLDOWN_SECONDS", "0")  # tests fluides
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
import tempfile  # noqa: E402

os.environ.setdefault("MEDIA_DIR", tempfile.mkdtemp(prefix="faso_media_"))
os.environ.setdefault("MEDIA_AUTO_APPROVE", "true")

import io  # noqa: E402
from datetime import date  # noqa: E402

import httpx  # noqa: E402
import pytest_asyncio  # noqa: E402
from PIL import Image  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402


def tiny_jpeg(color=(198, 93, 59)) -> bytes:
    """Image JPEG 64×64 minimale pour les uploads de test."""
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), color).save(buf, "JPEG")
    return buf.getvalue()


PHONE_COUNTER = {"n": 0}


def next_phone() -> str:
    """Génère un numéro burkinabè valide unique (7x xx xx xx)."""
    PHONE_COUNTER["n"] += 1
    return f"+2267{PHONE_COUNTER['n']:07d}"[:12]


@pytest_asyncio.fixture
async def db_engine():
    """Moteur SQLite en mémoire + schéma créé, isolé par test."""
    import app.models  # noqa: F401  (enregistre les modèles)
    from app.db.base import Base

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Session directe pour les tests de services / ajustements ORM."""
    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest_asyncio.fixture
async def app(db_engine):
    """Application FastAPI avec BDD de test et rate-limit désactivé."""
    from app.core.deps import get_db, get_session_factory
    from app.main import create_app

    Session = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with Session() as session:
            yield session

    application = create_app()
    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_session_factory] = lambda: Session
    application.state.limiter.enabled = False

    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app):
    """Client HTTP de test (ASGI, sans réseau)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def ws_setup():
    """Application pour tests WebSocket : SQLite **fichier** + NullPool.

    TestClient exécute l'app dans une boucle séparée (portail) ; un moteur
    en mémoire partagé entre boucles bloque. Avec NullPool chaque session
    ouvre sa connexion dans la boucle courante → aucun partage inter-boucle.
    """
    import app.models  # noqa: F401
    from app.core.deps import get_db, get_session_factory
    from app.db.base import Base
    from app.main import create_app
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{path}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with Session() as session:
            yield session

    application = create_app()
    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_session_factory] = lambda: Session
    application.state.limiter.enabled = False

    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        with TestClient(application) as tc:
            yield c, tc

    application.dependency_overrides.clear()
    await engine.dispose()
    os.unlink(path)


async def create_user(
    client,
    *,
    phone: str | None = None,
    display_name: str = "Kadiatou",
    gender: str = "female",
    age: int = 26,
    looking_for: str = "everyone",
    city: str = "Ouagadougou",
    latitude: float | None = 12.3714,
    longitude: float | None = -1.5197,
    with_photo: bool = True,
    bio: str = "À la recherche d'une belle rencontre.",
    interests: list[str] | None = None,
):
    """Crée un utilisateur complet : OTP → compte → profil (+photo).

    Retourne (user_id, access_token, headers).
    """
    phone = phone or next_phone()
    r = await client.post("/api/v1/auth/otp/request", json={"phone": phone})
    code = r.json()["dev_code"]
    birth = date(date.today().year - age, 6, 15).isoformat()
    r = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "code": code, "birthdate": birth},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.put(
        "/api/v1/profiles/me",
        json={
            "display_name": display_name,
            "gender": gender,
            "looking_for": looking_for,
            "bio": bio,
            "city": city,
            "interests": interests or ["Musique", "Voyage"],
            "latitude": latitude,
            "longitude": longitude,
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text

    if with_photo:
        r = await client.post(
            "/api/v1/profiles/me/photos",
            files={"file": ("photo.jpg", tiny_jpeg(), "image/jpeg")},
            headers=headers,
        )
        assert r.status_code == 201, r.text

    r = await client.get("/api/v1/auth/me", headers=headers)
    user_id = r.json()["id"]
    return user_id, token, headers


@pytest_asyncio.fixture
def make_user(client):
    """Fixture fine enveloppant create_user() pour le client HTTP de test."""

    async def _make(**kwargs):
        return await create_user(client, **kwargs)

    return _make


async def make_match(client, headers_a, headers_b, user_id_a, user_id_b) -> str:
    """Crée un match réciproque entre A et B, retourne match_id."""
    r = await client.post(
        "/api/v1/discover/react",
        json={"target_user_id": user_id_b, "action": "like"},
        headers=headers_a,
    )
    assert r.status_code == 200 and r.json()["matched"] is False
    r = await client.post(
        "/api/v1/discover/react",
        json={"target_user_id": user_id_a, "action": "like"},
        headers=headers_b,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["matched"] is True
    return body["match_id"]
