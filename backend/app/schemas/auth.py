"""Schémas Pydantic des flux d'authentification (entrées/sorties API)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class OtpRequestIn(BaseModel):
    """Demande d'envoi d'un code OTP par SMS."""

    # Pas de min_length ici : la validation de fond (message français, 400)
    # est faite par normalize_bf_phone(). On borne juste la taille brute.
    phone: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Numéro burkinabè : +226XXXXXXXX, 00226XXXXXXXX ou XXXXXXXX",
        examples=["+22670112233"],
    )


class OtpRequestOut(BaseModel):
    message: str
    # Renvoyé uniquement si OTP_DEV_ECHO=true (développement local).
    dev_code: str | None = None


class OtpVerifyIn(BaseModel):
    """Vérification du code OTP (connexion) ou création de compte (+naissance)."""

    phone: str = Field(..., min_length=1, max_length=20)
    code: str = Field(..., min_length=4, max_length=8, pattern=r"^\d+$")
    birthdate: date | None = Field(
        default=None,
        description="Obligatoire à la création de compte (règle 18+)",
        examples=["1998-04-23"],
    )


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Durée de vie de l'access token (s)")
    is_new_user: bool = False


class RefreshIn(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    """Vue publique du compte connecté."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    phone_e164: str
    birthdate: date
    age: int
    role: str
    is_verified: bool
    created_at: datetime
