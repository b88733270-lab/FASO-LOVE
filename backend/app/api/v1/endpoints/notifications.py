"""Phase 8 — notifications : appareils push (FCM) + cloche in-app.

- POST   /devices                     enregistrer l'appareil (idempotent)
- DELETE /devices/{token}             désenregistrer (déconnexion de l'app)
- GET    /notifications               cloche (50 dernières + badge non-lues)
- POST   /notifications/{id}/read     marquer une entrée comme lue
- POST   /notifications/read-all      tout marquer comme lu
- GET    /notifications/prefs         préférences (matches / messages)
- PUT    /notifications/prefs         mettre à jour les préférences

Messages d'erreur en français. Limites : 60/min (appareils/prefs),
30/min (lecture badge — appelé souvent par l'écran d'accueil).
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.notifications import (
    CountsOut,
    DeviceOut,
    DeviceRegisterIn,
    NotificationListOut,
    NotificationOut,
    NotificationPrefsOut,
    ReadAllOut,
)
from app.services.notifications import (
    list_notifications,
    mark_all_read,
    mark_read,
    prefs_of,
    register_device,
    save_prefs,
    unregister_device,
)

router = APIRouter(tags=["notifications"])


def _notif_out(n) -> NotificationOut:
    return NotificationOut(
        id=n.id,
        kind=n.kind,
        title=n.title,
        body=n.body,
        payload=n.payload or {},
        read=n.read_at is not None,
        created_at=n.created_at,
    )


# ------------------------------------------------------------- appareils


@router.post("/devices", response_model=DeviceOut, status_code=201)
@limiter.limit("60/minute")
async def post_device(
    body: DeviceRegisterIn,
    request: Request,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeviceOut:
    device = await register_device(db, me.id, body.platform, body.token.strip())
    return device


@router.delete("/devices/{token}", status_code=204)
@limiter.limit("60/minute")
async def delete_device(
    token: str,
    request: Request,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    removed = await unregister_device(db, me.id, token)
    if not removed:
        raise HTTPException(404, "Appareil introuvable")


# -------------------------------------------------------------- cloche


@router.get("/notifications", response_model=NotificationListOut)
@limiter.limit("120/minute")
async def get_notifications(
    request: Request,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationListOut:
    items, unread = await list_notifications(db, me.id)
    return NotificationListOut(
        items=[_notif_out(n) for n in items], unread_count=unread
    )


@router.get("/notifications/count", response_model=CountsOut)
@limiter.limit("240/minute")
async def get_unread_count(
    request: Request,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CountsOut:
    """Badge léger (appelé fréquemment par l'app sans charger la cloche)."""
    _, unread = await list_notifications(db, me.id)
    return CountsOut(unread_count=unread)


@router.post("/notifications/{notif_id}/read", response_model=NotificationOut)
@limiter.limit("60/minute")
async def post_read(
    notif_id: str,
    request: Request,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationOut:
    notif = await mark_read(db, notif_id, me.id)
    if notif is None:
        raise HTTPException(404, "Notification introuvable")
    return _notif_out(notif)


@router.post("/notifications/read-all", response_model=ReadAllOut)
@limiter.limit("60/minute")
async def post_read_all(
    request: Request,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReadAllOut:
    return ReadAllOut(updated=await mark_all_read(db, me.id))


# ------------------------------------------------------------ préférences


@router.get("/notifications/prefs", response_model=NotificationPrefsOut)
@limiter.limit("60/minute")
async def get_prefs(
    request: Request, me: User = Depends(get_current_user)
) -> NotificationPrefsOut:
    prefs = prefs_of(me)
    return NotificationPrefsOut(**prefs)


@router.put("/notifications/prefs", response_model=NotificationPrefsOut)
@limiter.limit("60/minute")
async def put_prefs(
    body: NotificationPrefsOut,
    request: Request,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPrefsOut:
    save_prefs(me, body.model_dump())
    await db.commit()
    return body
