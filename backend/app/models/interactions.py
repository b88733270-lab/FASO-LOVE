"""Interactions entre utilisateurs : réactions (like/pass/coup de cœur),
matchs réciproques et blocages.

- [Like] conserve aussi les « pass » : un profil passé n'est plus proposé
  (anti-revue), pendant un délai raisonnable côté requête discover.
- [Match] : paire canonique (user_low < user_high) → contrainte d'unicité,
  un seul match par couple quelle que soit la direction du like.
- [Block] : coupe toute visibilité et interaction dans les deux sens
  (découverte, like, match, messages).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import utcnow
from app.db.base import Base

LIKE_ACTIONS = ("like", "pass", "super_like")
POSITIVE_ACTIONS = ("like", "super_like")


def canonical_pair(a: str, b: str) -> tuple[str, str]:
    """Retourne la paire (bas, haut) triée — référence unique d'un couple."""
    return (a, b) if a < b else (b, a)


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (
        UniqueConstraint("from_user_id", "to_user_id", name="uq_like_pair"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    from_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    to_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(12), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("user_low", "user_high", name="uq_match_pair"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_low: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_high: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )

    def other_user_id(self, me: str) -> str:
        return self.user_high if self.user_low == me else self.user_low


class Block(Base):
    __tablename__ = "blocks"
    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_id", name="uq_block_pair"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    blocker_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    blocked_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
