"""Sécurité FASO LOVE : hachage de secrets, émission/vérification de JWT.

Choix assumés :
- Toutes les dates persistées sont en **UTC naïf** (`utcnow()`) pour rester
  portables entre PostgreSQL et SQLite (tests) sans ambiguïté de fuseau.
- Les codes OTP et refresh tokens ne sont jamais stockés en clair :
  uniquement leur empreinte SHA-256 (salée du contexte) est persistée.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import get_settings


def utcnow() -> datetime:
    """Horodatage UTC naïf (comparable partout, y compris SQLite)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_uuid() -> str:
    return str(uuid.uuid4())


def hash_secret(value: str, *, context: str = "") -> str:
    """Empreinte SHA-256 d'un secret à durée de vie courte (OTP, token)."""
    return hashlib.sha256(f"{context}:{value}".encode("utf-8")).hexdigest()


def _encode(payload: dict[str, Any]) -> str:
    settings = get_settings()
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(*, user_id: str, role: str) -> tuple[str, int]:
    """Retourne (token d'accès JWT, durée de vie en secondes)."""
    settings = get_settings()
    expires_in = settings.access_token_expire_minutes * 60
    now = utcnow()
    payload = {
        "type": "access",
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "jti": new_uuid(),
    }
    return _encode(payload), expires_in


def create_refresh_token(*, user_id: str) -> tuple[str, str, datetime]:
    """Retourne (refresh token JWT, jti, date d'expiration)."""
    settings = get_settings()
    now = utcnow()
    expires_at = now + timedelta(days=settings.refresh_token_expire_days)
    jti = new_uuid()
    payload = {
        "type": "refresh",
        "sub": user_id,
        "iat": now,
        "exp": expires_at,
        "jti": jti,
    }
    return _encode(payload), jti, expires_at


def decode_token(token: str) -> dict[str, Any]:
    """Décode et valide un JWT. Lève jwt.InvalidTokenError si invalide/expiré."""
    settings = get_settings()
    return jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
