"""Signalements d'utilisateurs (modération).

Le signalement est le mécanisme central de sécurité exigé par les stores :
tout utilisateur peut signaler ; l'équipe tranche dans la file admin.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import utcnow
from app.db.base import Base

REPORT_REASONS = (
    "fake_profile",  # faux profil / usurpation
    "scam",  # arnaque / demande d'argent
    "harassment",  # harcèlement
    "inappropriate_content",  # contenu inapproprié
    "underage",  # suspicion de mineur (18+ strict)
    "spam",
    "other",
)

REPORT_STATUSES = ("pending", "resolved", "dismissed")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    reporter_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    reported_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(30), nullable=False)
    details: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(
        String(10), default="pending", nullable=False
    )
    resolution: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
