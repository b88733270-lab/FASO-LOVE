"""Profil public d'un utilisateur FASO LOVE (1:1 avec User).

Séparé de [User] (identité) : le profil porte les données « rencontre ».
La géolocalisation est volontairement stockée ici et **jamais exposée telle
quelle** aux autres utilisateurs — seule une distance arrondie est publiée.
"""

from datetime import date, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import utcnow
from app.db.base import Base

# Valeurs autorisées (validées aussi par les schémas Pydantic).
GENDERS = ("female", "male")
LOOKING_FOR = ("female", "male", "everyone")


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[str] = mapped_column(String(60), nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    looking_for: Mapped[str] = mapped_column(
        String(10), default="everyone", nullable=False
    )
    bio: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    city: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    interests: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    @staticmethod
    def age_of(birthdate: date) -> int:
        today = utcnow().date()
        years = today.year - birthdate.year
        if (today.month, today.day) < (birthdate.month, birthdate.day):
            years -= 1
        return years
