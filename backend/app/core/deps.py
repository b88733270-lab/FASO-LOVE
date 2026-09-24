"""Dépendances FastAPI : session BDD et utilisateur courant (JWT Bearer)."""

from collections.abc import AsyncGenerator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Identifiants invalides ou session expirée. Veuillez vous reconnecter.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def get_session_factory() -> async_sessionmaker:
    """Fabrique de sessions (WebSockets ouvrent plusieurs sessions en cours
    de connexion). Surchargeable dans les tests via dependency_overrides."""
    return AsyncSessionLocal


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Valide l'access token Bearer et charge l'utilisateur actif correspondant."""
    if credentials is None:
        raise _CREDENTIALS_ERROR
    try:
        payload = decode_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise _CREDENTIALS_ERROR
    if payload.get("type") != "access" or not payload.get("sub"):
        raise _CREDENTIALS_ERROR

    user = await db.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR
    return user
