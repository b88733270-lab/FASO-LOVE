"""Phase 8 — schémas des notifications (appareils push + cloche in-app)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

DEVICE_PLATFORMS = ("android", "ios", "web")


class DeviceRegisterIn(BaseModel):
    platform: str = Field(..., pattern=r"^(android|ios|web)$")
    token: str = Field(..., min_length=8, max_length=512)


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    platform: str
    created_at: datetime


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    title: str
    body: str
    payload: dict
    read: bool
    created_at: datetime


class NotificationListOut(BaseModel):
    items: list[NotificationOut]
    unread_count: int


class ReadAllOut(BaseModel):
    updated: int


class NotificationPrefsOut(BaseModel):
    matches: bool
    messages: bool


class CountsOut(BaseModel):
    unread_count: int
