"""Endpoints d'authentification FASO LOVE : OTP SMS + JWT + règle 18+.

Flux :
1. `POST /auth/otp/request` → envoie un code (SMS) au numéro +226.
2. `POST /auth/otp/verify`  → valide le code ; crée le compte si nouveau
   (date de naissance obligatoire, **vérification 18+ côté serveur**) ;
   renvoie un couple access/refresh JWT.
3. `POST /auth/refresh`     → rotation du couple de jetons (l'ancien
   refresh token est révoqué — détection de réutilisation).
4. `POST /auth/logout`      → révocation du refresh token.
"""

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user, get_db
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_secret,
    utcnow,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    OtpRequestIn,
    OtpRequestOut,
    OtpVerifyIn,
    RefreshIn,
    TokenPair,
    UserOut,
)
from app.services.auth_service import (
    AgeRestrictionError,
    OtpRequestTooSoon,
    OtpVerificationError,
    PhoneValidationError,
    assert_adult,
    check_otp,
    compute_age,
    consume_otp,
    issue_otp,
    normalize_bf_phone,
)
from app.services.sms import get_sms_sender

router = APIRouter(prefix="/auth", tags=["authentification"])


def _normalize_or_400(raw_phone: str) -> str:
    try:
        return normalize_bf_phone(raw_phone)
    except PhoneValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post(
    "/otp/request",
    response_model=OtpRequestOut,
    summary="Demander un code de connexion par SMS",
)
@limiter.limit(get_settings().otp_request_rate_limit)
async def request_otp(
    request: Request,
    body: OtpRequestIn,
    db: AsyncSession = Depends(get_db),
) -> OtpRequestOut:
    phone = _normalize_or_400(body.phone)
    try:
        code = await issue_otp(db, phone)
    except OtpRequestTooSoon as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)
        ) from exc

    await get_sms_sender().send_otp(phone, code)

    settings = get_settings()
    return OtpRequestOut(
        message="Code de vérification envoyé par SMS.",
        dev_code=code if settings.otp_dev_echo else None,
    )


@router.post(
    "/otp/verify",
    response_model=TokenPair,
    summary="Vérifier le code et obtenir une session",
)
@limiter.limit(get_settings().otp_verify_rate_limit)
async def verify_otp_endpoint(
    request: Request,
    body: OtpVerifyIn,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    phone = _normalize_or_400(body.phone)

    try:
        await check_otp(db, phone, body.code)
    except OtpVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    # Le code est valide → le numéro est prouvé. Compte existant ou création.
    user = await db.scalar(select(User).where(User.phone_e164 == phone))
    is_new_user = user is None

    if is_new_user:
        if body.birthdate is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La date de naissance est requise pour créer un compte.",
            )
        try:
            assert_adult(body.birthdate)  # règle 18+ — côté serveur, jamais client
        except AgeRestrictionError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
            ) from exc
        user = User(phone_e164=phone, birthdate=body.birthdate, is_verified=True)
        db.add(user)
        await db.flush()  # matérialise user.id

    # Toutes les validations sont passées : le code OTP est consommé
    # (usage unique) juste avant l'émission des jetons.
    await consume_otp(db, phone)

    user.last_login_at = utcnow()

    access_token, expires_in = create_access_token(user_id=user.id, role=user.role)
    refresh_token, jti, expires_at = create_refresh_token(user_id=user.id)
    db.add(
        RefreshToken(
            id=jti,
            user_id=user.id,
            token_hash=hash_secret(refresh_token, context=user.id),
            expires_at=expires_at,
        )
    )
    await db.commit()

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        is_new_user=is_new_user,
    )


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Renouveler la session (rotation du refresh token)",
)
async def refresh(
    body: RefreshIn,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    invalid = _unauthorized(
        "Session expirée. Veuillez vous reconnecter avec votre numéro."
    )
    try:
        payload = decode_token(body.refresh_token)
    except jwt.InvalidTokenError:
        raise invalid
    if payload.get("type") != "refresh" or not payload.get("sub"):
        raise invalid

    user_id: str = payload["sub"]
    stored = await db.get(RefreshToken, payload.get("jti", ""))
    if stored is None or stored.is_revoked or stored.expires_at <= utcnow():
        raise invalid
    if stored.user_id != user_id or stored.token_hash != hash_secret(
        body.refresh_token, context=user_id
    ):
        # Empreinte incohérente = jeton potentiellement forgé → révocation.
        stored.is_revoked = True
        await db.commit()
        raise invalid

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise invalid

    # Rotation : l'ancien jeton est révoqué, un nouveau couple est émis.
    stored.is_revoked = True
    access_token, expires_in = create_access_token(user_id=user.id, role=user.role)
    new_refresh, new_jti, expires_at = create_refresh_token(user_id=user.id)
    db.add(
        RefreshToken(
            id=new_jti,
            user_id=user.id,
            token_hash=hash_secret(new_refresh, context=user.id),
            expires_at=expires_at,
        )
    )
    await db.commit()

    return TokenPair(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=expires_in,
        is_new_user=False,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Déconnexion (révocation du refresh token)",
)
async def logout(
    body: RefreshIn,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Révocation best-effort : un jeton déjà invalide est simplement ignoré."""
    try:
        payload = decode_token(body.refresh_token)
    except jwt.InvalidTokenError:
        return None
    if payload.get("type") == "refresh" and payload.get("jti"):
        stored = await db.get(RefreshToken, payload["jti"])
        if stored is not None and not stored.is_revoked:
            stored.is_revoked = True
            await db.commit()
    return None


@router.get(
    "/me",
    response_model=UserOut,
    summary="Informations du compte connecté",
)
async def read_me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=user.id,
        phone_e164=user.phone_e164,
        birthdate=user.birthdate,
        age=compute_age(user.birthdate),
        role=user.role,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )
