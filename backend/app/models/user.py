"""Modèle utilisateur FASO LOVE.

Phase 1 : identité minimale (téléphone vérifié + date de naissance, règle
18+). Le profil riche (photos, bio, géolocalisation…) arrive en phase 2.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import utcnow
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    # String(36) pour rester portable SQLite/PostgreSQL (optimisation en
    # UUID natif possible ultérieurement).
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    phone_e164: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    birthdate: Mapped[date] = mapped_column(Date, nullable=False)

    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    # Phase 8 — préférences de notification (JSONB ; NULL = tout activé).
    notification_prefs: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
