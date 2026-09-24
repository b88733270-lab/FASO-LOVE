"""Modèles SQLAlchemy FASO LOVE (import central pour Alembic)."""

from app.models.interactions import Block, Like, Match
from app.models.message import Message
from app.models.notifications import Notification, PushDevice
from app.models.otp_code import OtpCode
from app.models.payments import PaymentTransaction, Subscription
from app.models.profile import Profile
from app.models.profile_photo import ProfilePhoto
from app.models.refresh_token import RefreshToken
from app.models.report import Report
from app.models.user import User

__all__ = [
    "User",
    "OtpCode",
    "RefreshToken",
    "Profile",
    "ProfilePhoto",
    "Like",
    "Match",
    "Block",
    "Message",
    "Report",
    "PaymentTransaction",
    "Subscription",
    "Notification",
    "PushDevice",
]
