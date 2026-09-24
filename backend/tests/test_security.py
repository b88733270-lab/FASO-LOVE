"""Tests de la couche sécurité : JWT (émission, décodage, expiration)."""

from datetime import timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    new_uuid,
    utcnow,
)


def test_access_token_cycle():
    token, expires_in = create_access_token(user_id="u123", role="user")
    assert expires_in > 0
    payload = decode_token(token)
    assert payload["type"] == "access"
    assert payload["sub"] == "u123"
    assert payload["role"] == "user"
    assert payload["jti"]


def test_refresh_token_cycle():
    token, jti, expires_at = create_refresh_token(user_id="u123")
    payload = decode_token(token)
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti
    assert expires_at > utcnow()


def test_token_expire_rejete():
    settings = get_settings()
    forged = jwt.encode(
        {
            "type": "access",
            "sub": "u123",
            "iat": utcnow() - timedelta(hours=2),
            "exp": utcnow() - timedelta(hours=1),
            "jti": new_uuid(),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(forged)


def test_token_mauvaise_signature_rejete():
    forged = jwt.encode(
        {"type": "access", "sub": "u123", "jti": new_uuid()},
        "mauvais-secret",
        algorithm="HS256",
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(forged)


def test_uuid_uniques():
    assert new_uuid() != new_uuid()
