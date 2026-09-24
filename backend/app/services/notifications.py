"""Phase 8 — service de notifications : cloche in-app + push Mobile (FCM).

Architecture :

- **In-app** : chaque événement (match, message) insère une ligne
  ``notifications`` respectant les préférences de l'utilisateur
  (``users.notification_prefs`` JSONB ; absent = tout activé).
- **Push** : abstraction ``PushProvider``. ``log`` (défaut DEV) se borne à
  journaliser — le parcours applicatif est donc certifiable SANS compte
  Firebase, exactement comme la passerelle ``mock`` des paiements.
  ``fcm`` appelle l'API HTTP legacy Firebase Cloud Messaging quand
  ``FCM_SERVER_KEY`` est fournie (production).
- Le push est **best-effort** : un échec (réseau, jeton invalide) casse
  silencieusement en warning, jamais l'événement métier.

Anti-spam : deuxième message non lu DANS LE MÊME MATCH → notification déjà
présente, on ne ré-empile pas (la cloche affiche 1 entrée par conversation).
"""

from typing import Protocol

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import utcnow
from app.models.notifications import Notification, PushDevice
from app.models.profile import Profile
from app.models.user import User

logger = logging.getLogger("fasolove.notifications")

KIND_MATCH = "match"
KIND_MESSAGE = "message"

# Préférences par défaut (clés stables, stockage JSONB sur users).
DEFAULT_PREFS: dict[str, bool] = {"matches": True, "messages": True}
_PREFS_OF_KIND = {KIND_MATCH: "matches", KIND_MESSAGE: "messages"}

MAX_NOTIFICATIONS = 50  # profondeur de la cloche in-app


# ------------------------------------------------------------------ helpers


def prefs_of(user: User) -> dict[str, bool]:
    """Préférences effectives (défauts + remplacements stockés)."""
    stored = user.notification_prefs or {}
    return {
        key: bool(stored.get(key, default))
        for key, default in DEFAULT_PREFS.items()
    }


def save_prefs(user: User, prefs: dict[str, bool]) -> None:
    """N'enregistre QUE les clés connues (booléens stricts)."""
    user.notification_prefs = {
        key: bool(prefs[key]) for key in DEFAULT_PREFS if key in prefs
    }


# ------------------------------------------------------------------- push


class PushProvider(Protocol):
    async def send(self, token: str, title: str, body: str, payload: dict) -> bool:
        """Retourne True si acceptée côté service push, False si jeton mort."""


class LogPushProvider:
    """Sandbox : journalise au lieu d'envoyer (parcours = production)."""

    async def send(self, token: str, title: str, body: str, payload: dict) -> bool:
        logger.info(
            "📲 PUSH (sandbox, DEV SEULEMENT) → %s… : %s — %s",
            token[:18], title, body[:80],
        )
        return True


class FcmPushProvider:
    """Firebase Cloud Messaging (API HTTP legacy — production)."""

    ENDPOINT = "https://fcm.googleapis.com/fcm/send"

    def __init__(self) -> None:
        import httpx  # déjà requis par PayDunya (Phase 7)

        key = get_settings().fcm_server_key
        if not key:
            raise RuntimeError(
                "PUSH_PROVIDER=fcm sans FCM_SERVER_KEY — définir la clé "
                "serveur du projet Firebase (console Firebase > Paramètres > "
                "Cloud Messaging). Jamais côté client."
            )
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"key={key}"}, timeout=10.0
        )

    async def send(self, token: str, title: str, body: str, payload: dict) -> bool:
        r = await self._client.post(
            self.ENDPOINT,
            json={
                "to": token,
                "notification": {"title": title, "body": body[:120]},
                "data": {k: str(v) for k, v in payload.items()},
            },
        )
        data = r.json() if r.headers.get("content-type", "").startswith(
            "application/json"
        ) else {}
        # (legacy API) failure=1 + NotRegistered → jeton mort → nettoyage.
        if r.status_code == 200 and data.get("failure") == 0:
            return True
        return False


def get_push_provider() -> PushProvider:
    if get_settings().push_provider == "fcm":
        return FcmPushProvider()
    return LogPushProvider()


# ------------------------------------------------------------ core : notify


async def register_device(
    db: AsyncSession, user_id: str, platform: str, token: str
) -> PushDevice:
    """Enregistrement idempotent : un jeton FCM = un appareil.

    Le même jeton peut changer d'utilisateur (en déconnexion/reconnexion
    sur le même téléphone) → ré-attribution.
    """
    device = await db.scalar(select(PushDevice).where(PushDevice.token == token))
    if device is not None:
        device.user_id = user_id
        device.platform = platform
        device.updated_at = utcnow()
    else:
        device = PushDevice(user_id=user_id, platform=platform, token=token)
        db.add(device)
    await db.commit()
    return device


async def unregister_device(db: AsyncSession, user_id: str, token: str) -> bool:
    device = await db.scalar(
        select(PushDevice).where(
            PushDevice.token == token, PushDevice.user_id == user_id
        )
    )
    if device is None:
        return False
    await db.delete(device)
    await db.commit()
    return True


async def _push_to_user(
    db: AsyncSession, user_id: str, title: str, body: str, payload: dict
) -> None:
    """Push best-effort sur tous les appareils du destinataire ; purge les
    jetons morts signalés par le prestataire."""
    devices = (
        (await db.execute(select(PushDevice).where(PushDevice.user_id == user_id)))
        .scalars()
        .all()
    )
    if not devices:
        return
    try:
        provider = get_push_provider()
    except RuntimeError as exc:  # fcm sans clé : warning, jamais critique
        logger.warning("push désactivé : %s", exc)
        return
    dead: list[PushDevice] = []
    for device in devices:
        try:
            ok = await provider.send(device.token, title, body, payload)
        except Exception as exc:  # réseau/timeout : silencieux par conception
            logger.warning("push échoué (appareil %s) : %s", device.id, str(exc)[:120])
            continue
        if not ok:
            dead.append(device)
    for device in dead:
        await db.delete(device)
    if dead:
        await db.commit()


async def notify_user(
    db: AsyncSession,
    user_id: str,
    kind: str,
    title: str,
    body: str,
    payload: dict,
) -> Notification | None:
    """Crée la notification in-app (si préférence active) puis tente le push.

    Retourne la notification créée, ou ``None`` si l'utilisateur a désactivé
    ce canal (préférence) ou qu'un doublon utile existe (message non lu du
    même match).
    """
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    prefs = prefs_of(user)
    pref_key = _PREFS_OF_KIND.get(kind)
    if pref_key is not None and not prefs.get(pref_key, True):
        return None  # canal désactivé par l'utilisateur

    # Anti-spam : déjà une notification NON LUE du même match → on n'empile pas.
    if kind == KIND_MESSAGE and payload.get("match_id"):
        existing = await db.scalar(
            select(Notification.id).where(
                Notification.user_id == user_id,
                Notification.kind == KIND_MESSAGE,
                Notification.read_at.is_(None),
                Notification.payload["match_id"].as_string() == payload["match_id"],
            )
        )
        if existing is not None:
            return None

    notif = Notification(
        user_id=user_id, kind=kind, title=title[:120], body=body[:300], payload=payload
    )
    db.add(notif)
    await db.commit()
    await _push_to_user(db, user_id, notif.title, notif.body, payload)
    return notif


async def display_name_of(db: AsyncSession, user_id: str) -> str:
    name = await db.scalar(
        select(Profile.display_name).where(Profile.user_id == user_id)
    )
    return name or "Une personne"


async def notify_match_created(db: AsyncSession, match) -> None:
    """Notifie les DEUX membres d'un nouveau match (événement star ⭐)."""
    for me_id, peer_id in (
        (match.user_low, match.user_high),
        (match.user_high, match.user_low),
    ):
        peer_name = await display_name_of(db, peer_id)
        await notify_user(
            db,
            me_id,
            KIND_MATCH,
            "Nouveau match 🎉",
            f"Vous et {peer_name} vous êtes plu mutuellement 💛",
            {"match_id": match.id, "peer_id": peer_id, "peer_name": peer_name},
        )


async def notify_message_received(
    db: AsyncSession, match_id: str, sender_id: str, content: str
) -> None:
    """Notifie le destinataire d'un nouveau message (aperçu tronqué)."""
    from app.models.interactions import Match  # éviter le cycle d'imports

    match = await db.get(Match, match_id)
    if match is None:
        return
    recipient_id = match.other_user_id(sender_id)
    sender_name = await display_name_of(db, sender_id)
    preview = content if len(content) <= 80 else content[:77] + "…"
    await notify_user(
        db,
        recipient_id,
        KIND_MESSAGE,
        f"💬 {sender_name}",
        preview,
        {"match_id": match_id, "peer_id": sender_id, "peer_name": sender_name},
    )


# ------------------------------------------------------------------- lecture


async def list_notifications(
    db: AsyncSession, user_id: str
) -> tuple[list[Notification], int]:
    """Dernières notifs (50) + compteur de non-lues (badge cloche)."""
    items = (
        (
            await db.execute(
                select(Notification)
                .where(Notification.user_id == user_id)
                .order_by(Notification.created_at.desc())
                .limit(MAX_NOTIFICATIONS)
            )
        )
        .scalars()
        .all()
    )
    unread = await db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.read_at.is_(None)
        )
    )
    return items, int(unread or 0)


async def mark_read(
    db: AsyncSession, notification_id: str, user_id: str
) -> Notification | None:
    notif = await db.get(Notification, notification_id)
    if notif is None or notif.user_id != user_id:
        return None
    if notif.read_at is None:
        notif.read_at = utcnow()
        await db.commit()
    return notif


async def mark_all_read(db: AsyncSession, user_id: str) -> int:
    items = (
        (
            await db.execute(
                select(Notification).where(
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    now = utcnow()
    for notif in items:
        notif.read_at = now
    await db.commit()
    return len(items)


# ------------------------------------------------------------ KPIs (admin)


async def notifications_total(db: AsyncSession) -> int:
    return int(await db.scalar(select(func.count(Notification.id))) or 0)


async def push_devices_total(db: AsyncSession) -> int:
    return int(await db.scalar(select(func.count(PushDevice.id))) or 0)
