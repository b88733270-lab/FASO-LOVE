"""Phase 8 — notifications : centre in-app + appareils push (FCM).

Deux tables :

- ``notifications`` : cloche in-app persistante (match reçu, message reçu),
  avec préférences utilisateur (stockées en JSONB sur ``users``) ;
- ``push_devices`` : jetons FCM des appareils, pour les notifications push
  natives (écran verrouillé). Un jeton appartient à UN utilisateur et est
  réenregistré idempotemment (changement de device token côté FCM).
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import utcnow
from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # kind : "match" | "message"
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    body: Mapped[str] = mapped_column(String(300), nullable=False)
    # Routage côté app : {"match_id": …, "peer_id": …, "peer_name": …}
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )

    __table_args__ = (
        Index("ix_notifications_user_recent", "user_id", "created_at"),
        Index("ix_notifications_user_unread", "user_id", "read_at"),
    )


class PushDevice(Base):
    __tablename__ = "push_devices"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(10), nullable=False)  # android/ios/web
    token: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    __table_args__ = (
        UniqueConstraint("token", name="uq_push_devices_token"),
        Index("ix_push_devices_user", "user_id"),
    )
