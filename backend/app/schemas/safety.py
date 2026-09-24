"""Schémas de sécurité sociale (blocages, signalements) et d'administration."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.report import REPORT_REASONS


class BlockIn(BaseModel):
    user_id: str


class BlockOut(BaseModel):
    user_id: str
    created_at: datetime


class ReportIn(BaseModel):
    reported_user_id: str
    reason: str = Field(..., description=f"Valeurs : {', '.join(REPORT_REASONS)}")
    details: str = Field(default="", max_length=2000)


class ReportOut(BaseModel):
    id: str
    reported_user_id: str
    reason: str
    status: str
    message: str = "Merci pour votre signalement. Notre équipe va l'examiner."


# ---------- Administration ----------


class AdminStatsOut(BaseModel):
    users_total: int
    users_verified: int
    users_active_today: int
    profiles_with_photo: int
    matches_total: int
    messages_total: int
    reports_pending: int
    photos_pending: int
    # Monétisation (Phase 7)
    subscriptions_active: int = 0
    payments_succeeded: int = 0
    revenue_fcfa_total: int = 0


class AdminReportItem(BaseModel):
    id: str
    reporter_id: str
    reported_id: str
    reported_name: str | None
    reason: str
    details: str
    status: str
    created_at: datetime


class ResolveReportIn(BaseModel):
    resolution: str = Field(..., description="'resolved' ou 'dismissed'")


class AdminUserItem(BaseModel):
    id: str
    phone_e164: str
    age: int | None
    role: str
    is_active: bool
    is_verified: bool
    display_name: str | None
    city: str | None
    created_at: datetime


class AdminUserPatch(BaseModel):
    is_active: bool | None = None
    role: str | None = Field(default=None, description="'user' ou 'admin'")


class AdminPhotoItem(BaseModel):
    id: str
    user_id: str
    url: str
    status: str
    created_at: datetime


class ModeratePhotoIn(BaseModel):
    action: str = Field(..., description="'approve' ou 'reject'")
