"""Tests du service OTP (cycle émission → vérification → consommation)."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.security import hash_secret, utcnow
from app.models.otp_code import OtpCode
from app.services.auth_service import (
    OtpRequestTooSoon,
    OtpVerificationError,
    check_otp,
    consume_otp,
    issue_otp,
)


async def test_emission_verification_consommation(db_session):
    code = await issue_otp(db_session, "+22670112233")
    await check_otp(db_session, "+22670112233", code)  # valide, non consommé
    await consume_otp(db_session, "+22670112233")
    # Après consommation, le même code ne passe plus.
    with pytest.raises(OtpVerificationError):
        await check_otp(db_session, "+22670112233", code)


async def test_mauvais_code_incremente_et_verrouille(db_session):
    settings = get_settings()
    await issue_otp(db_session, "+22670112233")
    for _ in range(settings.otp_max_attempts):
        with pytest.raises(OtpVerificationError):
            await check_otp(db_session, "+22670112233", "999999")
    # Verrouillé : plus aucun code en attente → nouvel envoi SMS nécessaire.
    pending = await db_session.scalar(
        select(func.count())
        .select_from(OtpCode)
        .where(
            OtpCode.phone_e164 == "+22670112233",
            OtpCode.is_consumed.is_(False),
        )
    )
    assert pending == 0


async def test_code_expire_refuse(db_session):
    code = await issue_otp(db_session, "+22670112233")
    # On fait expirer artificiellement le code.
    otp = await db_session.scalar(
        select(OtpCode).order_by(OtpCode.created_at.desc()).limit(1)
    )
    otp.expires_at = utcnow() - timedelta(seconds=1)
    await db_session.commit()
    with pytest.raises(OtpVerificationError):
        await check_otp(db_session, "+22670112233", code)


async def test_anti_spam_renvoi(db_session):
    """Deux demandes rapprochées → refus (cooldown forcé pour ce test)."""
    settings = get_settings()
    original = settings.otp_resend_cooldown_seconds
    settings.otp_resend_cooldown_seconds = 60  # environnement de test : 0 par défaut
    try:
        await issue_otp(db_session, "+22670112233")
        with pytest.raises(OtpRequestTooSoon):
            await issue_otp(db_session, "+22670112233")
    finally:
        settings.otp_resend_cooldown_seconds = original


def test_hash_secret_contexte():
    a = hash_secret("123456", context="+22670112233")
    b = hash_secret("123456", context="+22665098877")
    assert a != b  # même code, contextes différents
    assert a == hash_secret("123456", context="+22670112233")  # déterministe
