"""Logique métier d'authentification FASO LOVE.

- Normalisation des numéros burkinabè (+226) — les formats acceptés :
  `+226XXXXXXXX`, `00226XXXXXXXX`, ou `XXXXXXXX` (8 chiffres, mobile).
- Cycle OTP : émission (avec anti-spam), vérification stricte, tentatives
  plafonnées, consommation à usage unique.
- Vérification d'âge : application **strictement réservée aux adultes** ;
  le calcul est fait côté serveur (jamais côté client).
"""

import secrets
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_secret, utcnow
from app.models.otp_code import OtpCode

# Préfixes mobiles du Burkina Faso : 5x (Moov), 6x (Moov), 7x (Orange),
# d'autres opérateurs (Telecel) partagent ces blocs — on valide la forme,
# pas l'opérateur.
_MOBILE_FIRST_DIGITS = {"5", "6", "7"}


class PhoneValidationError(ValueError):
    """Numéro burkinabè invalide."""


def normalize_bf_phone(raw: str) -> str:
    """Normalise un numéro au format E.164 (+226XXXXXXXX).

    Lève PhoneValidationError si le numéro n'est pas un mobile burkinabè
    de 8 chiffres.
    """
    digits = "".join(c for c in raw if c.isdigit())
    if digits.startswith("00226"):
        digits = digits[5:]
    elif digits.startswith("226") and len(digits) == 11:
        digits = digits[3:]

    if len(digits) != 8:
        raise PhoneValidationError(
            "Numéro invalide : 8 chiffres attendus (ex. +226 70 11 22 33)."
        )
    if digits[0] not in _MOBILE_FIRST_DIGITS:
        raise PhoneValidationError(
            "Numéro invalide : veuillez saisir un numéro de mobile burkinabè."
        )
    return f"+226{digits}"


def compute_age(birthdate: date, *, today: date | None = None) -> int:
    """Âge exact en années révolues (anniversaire non atteint = -1)."""
    today = today or utcnow().date()
    years = today.year - birthdate.year
    if (today.month, today.day) < (birthdate.month, birthdate.day):
        years -= 1
    return years


class AgeRestrictionError(ValueError):
    """Âge hors limites autorisées (règle 18+ stricte)."""


def assert_adult(birthdate: date) -> None:
    """Vérifie la règle d'âge (18+ strict côté serveur).

    Lève AgeRestrictionError avec un message utilisateur en français.
    """
    settings = get_settings()
    if birthdate > utcnow().date():
        raise AgeRestrictionError("Date de naissance invalide (dans le futur).")
    age = compute_age(birthdate)
    if age < settings.min_age:
        raise AgeRestrictionError(
            "FASO LOVE est réservé aux personnes de 18 ans et plus."
        )
    if age > settings.max_age:
        raise AgeRestrictionError("Date de naissance invalide. Veuillez vérifier.")


def generate_otp() -> str:
    """Code OTP numérique aléatoire (cryptographiquement sûr)."""
    settings = get_settings()
    return f"{secrets.randbelow(10**settings.otp_length):0{settings.otp_length}d}"


class OtpRequestTooSoon(Exception):
    """Redemande d'OTP avant la fin du délai anti-spam."""


async def issue_otp(db: AsyncSession, phone_e164: str) -> str:
    """Crée un OTP valide et retourne le code en clair (pour l'envoi SMS).

    Respecte un délai minimal entre deux demandes (anti-spam SMS, coût).
    """
    settings = get_settings()
    now = utcnow()

    latest = await db.scalar(
        select(OtpCode)
        .where(OtpCode.phone_e164 == phone_e164)
        .order_by(OtpCode.created_at.desc())
        .limit(1)
    )
    if latest is not None:
        elapsed = (now - latest.created_at).total_seconds()
        if elapsed < settings.otp_resend_cooldown_seconds:
            raise OtpRequestTooSoon(
                "Un code vient d'être envoyé. "
                "Veuillez patienter avant d'en redemander un."
            )

    code = generate_otp()
    otp = OtpCode(
        phone_e164=phone_e164,
        code_hash=hash_secret(code, context=phone_e164),
        expires_at=now + timedelta(minutes=settings.otp_ttl_minutes),
    )
    db.add(otp)
    await db.commit()
    return code


class OtpVerificationError(ValueError):
    """Code OTP invalide, expiré ou trop de tentatives."""


async def _latest_pending_otp(db: AsyncSession, phone_e164: str) -> OtpCode | None:
    return await db.scalar(
        select(OtpCode)
        .where(OtpCode.phone_e164 == phone_e164, OtpCode.is_consumed.is_(False))
        .order_by(OtpCode.created_at.desc())
        .limit(1)
    )


async def check_otp(db: AsyncSession, phone_e164: str, code: str) -> None:
    """Vérifie un code OTP **sans le consommer**.

    La consommation (`consume_otp`) n'intervient qu'une fois toutes les
    autres validations métier passées (ex. date de naissance, règle 18+),
    afin de ne pas gaspiller de SMS en cas d'erreur de saisie.
    Chaque code incorrect incrémente le compteur de tentatives et peut
    verrouiller le code (nouveau SMS nécessaire).
    """
    settings = get_settings()

    otp = await _latest_pending_otp(db, phone_e164)
    if otp is None or otp.expires_at <= utcnow():
        raise OtpVerificationError("Code invalide ou expiré. Redemandez un code.")

    expected = hash_secret(code, context=phone_e164)
    if not secrets.compare_digest(otp.code_hash, expected):
        otp.attempts += 1
        if otp.attempts >= settings.otp_max_attempts:
            otp.is_consumed = True  # verrouillage : nouveau code nécessaire
        await db.commit()
        raise OtpVerificationError("Code incorrect. Veuillez réessayer.")


async def consume_otp(db: AsyncSession, phone_e164: str) -> None:
    """Invalide le dernier code en attente (usage unique)."""
    otp = await _latest_pending_otp(db, phone_e164)
    if otp is not None:
        otp.is_consumed = True
        await db.commit()
