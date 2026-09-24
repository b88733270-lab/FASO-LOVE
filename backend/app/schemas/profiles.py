"""Schémas des profils et de la découverte."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.interactions import LIKE_ACTIONS
from app.models.profile import GENDERS, LOOKING_FOR

MAX_INTERESTS = 10


class ProfileIn(BaseModel):
    """Création/mise à jour de son propre profil (upsert)."""

    display_name: str = Field(..., min_length=2, max_length=60)
    gender: str = Field(..., description=f"Valeurs : {', '.join(GENDERS)}")
    looking_for: str = Field(
        default="everyone", description=f"Valeurs : {', '.join(LOOKING_FOR)}"
    )
    bio: str = Field(default="", max_length=500)
    city: str = Field(default="", max_length=80)
    interests: list[str] = Field(default_factory=list, max_length=MAX_INTERESTS)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("gender")
    @classmethod
    def _check_gender(cls, v: str) -> str:
        if v not in GENDERS:
            raise ValueError(f"genre invalide (attendu : {', '.join(GENDERS)})")
        return v

    @field_validator("looking_for")
    @classmethod
    def _check_looking_for(cls, v: str) -> str:
        if v not in LOOKING_FOR:
            raise ValueError(
                f"looking_for invalide (attendu : {', '.join(LOOKING_FOR)})"
            )
        return v

    @field_validator("interests")
    @classmethod
    def _clean_interests(cls, v: list[str]) -> list[str]:
        return [i.strip() for i in v if i.strip()][:MAX_INTERESTS]


class PhotoOut(BaseModel):
    id: str
    url: str
    status: str


class ProfilePublic(BaseModel):
    """Vue publique d'un profil (jamais de coordonnées exactes)."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str
    display_name: str
    gender: str
    age: int
    bio: str
    city: str
    interests: list[str]
    photos: list[PhotoOut]
    distance_km: float | None = None


class ProfileMine(ProfilePublic):
    """Mon propre profil : inclut position + statistiques utiles."""

    looking_for: str
    latitude: float | None = None
    longitude: float | None = None
    updated_at: datetime


class DiscoverQuery(BaseModel):
    min_age: int = Field(default=18, ge=18)
    max_age: int = Field(default=60, le=99)
    max_distance_km: float | None = Field(default=None, gt=0, le=1000)
    limit: int = Field(default=20, ge=1, le=50)


class ReactionIn(BaseModel):
    target_user_id: str
    action: str = Field(..., description=f"Valeurs : {', '.join(LIKE_ACTIONS)}")


class ReactionOut(BaseModel):
    matched: bool = False
    match_id: str | None = None
    detail: str = "Réaction enregistrée."
    message: str = ""


class PeerSummary(BaseModel):
    """Résumé du correspondant dans la liste des matchs."""

    user_id: str
    display_name: str
    age: int
    city: str
    photo_url: str | None
    interests: list[str]


class MatchOut(BaseModel):
    match_id: str
    created_at: datetime
    peer: PeerSummary
    last_message: "MessageOut | None" = None
    unread_count: int = 0


class MessageOut(BaseModel):
    id: str
    sender_id: str
    content: str
    created_at: datetime
    read_at: datetime | None = None
    is_mine: bool = False


MatchOut.model_rebuild()
