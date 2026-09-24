"""Photos de profil (pipeline de modération).

Cycle de vie : pending → approved | rejected.
- En dev (`MEDIA_AUTO_APPROVE=true`) l'approbation est automatique ;
- en production, une photo n'apparaît qu'après validation (file de
  modération admin — voir endpoints /admin/photos).
Seules les photos `approved` sont visibles publiquement.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import utcnow
from app.db.base import Base

PHOTO_STATUSES = ("pending", "approved", "rejected")


class ProfilePhoto(Base):
    __tablename__ = "profile_photos"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(10), default="pending", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )

    @property
    def url(self) -> str:
        return f"/media/{self.file_path}"
