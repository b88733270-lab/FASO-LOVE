"""Endpoints d'administration FASO LOVE (rôle `admin` requis).

Back-office d'abord conçu pour le dashboard Flutter Web (phase 5) ;
toutes les routes sont aussi testables via /docs.
Le rôle admin s'attribue hors API : `python tools_make_admin.py <téléphone>`.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.security import utcnow
from app.models.message import Message
from app.models.interactions import Match
from app.models.notifications import Notification, PushDevice
from app.models.payments import PaymentTransaction, Subscription
from app.models.profile import Profile
from app.models.profile_photo import ProfilePhoto
from app.models.report import Report
from app.models.user import User
from app.schemas.safety import (
    AdminPhotoItem,
    AdminReportItem,
    AdminStatsOut,
    AdminUserItem,
    AdminUserPatch,
    ModeratePhotoIn,
    ResolveReportIn,
)
from app.services.media import delete_profile_photo

router = APIRouter(prefix="/admin", tags=["administration"])


async def require_admin(me: User = Depends(get_current_user)) -> User:
    if me.role != "admin":
        raise HTTPException(403, "Accès réservé à l'équipe FASO LOVE.")
    return me


@router.get("/stats", response_model=AdminStatsOut)
async def stats(
    admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> AdminStatsOut:
    day_start = utcnow() - timedelta(days=1)
    async def count(stmt) -> int:
        return int(await db.scalar(stmt) or 0)

    return AdminStatsOut(
        users_total=await count(select(func.count()).select_from(User)),
        users_verified=await count(
            select(func.count()).select_from(User).where(User.is_verified.is_(True))
        ),
        users_active_today=await count(
            select(func.count())
            .select_from(User)
            .where(User.last_login_at >= day_start)
        ),
        profiles_with_photo=await count(
            select(func.count(func.distinct(ProfilePhoto.user_id))).where(
                ProfilePhoto.status == "approved"
            )
        ),
        matches_total=await count(select(func.count()).select_from(Match)),
        messages_total=await count(select(func.count()).select_from(Message)),
        reports_pending=await count(
            select(func.count()).select_from(Report).where(Report.status == "pending")
        ),
        photos_pending=await count(
            select(func.count())
            .select_from(ProfilePhoto)
            .where(ProfilePhoto.status == "pending")
        ),
        # — Monétisation (Phase 7) —
        subscriptions_active=await count(
            select(func.count())
            .select_from(Subscription)
            .where(
                Subscription.status == "active",
                Subscription.ends_at > utcnow(),
            )
        ),
        payments_succeeded=await count(
            select(func.count())
            .select_from(PaymentTransaction)
            .where(PaymentTransaction.status == "succeeded")
        ),
        revenue_fcfa_total=int(
            await db.scalar(
                select(func.coalesce(func.sum(PaymentTransaction.amount_fcfa), 0)).where(
                    PaymentTransaction.status == "succeeded"
                )
            )
        ),
        # — Notifications (Phase 8) —
        notifications_total=await count(
            select(func.count()).select_from(Notification)
        ),
        push_devices_total=await count(
            select(func.count()).select_from(PushDevice)
        ),
    )


@router.get("/reports", response_model=list[AdminReportItem])
async def list_reports(
    status_filter: str = Query("pending", description="pending|resolved|dismissed|all"),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AdminReportItem]:
    stmt = select(Report).order_by(Report.created_at.desc()).limit(limit)
    if status_filter != "all":
        stmt = stmt.where(Report.status == status_filter)
    reports = (await db.execute(stmt)).scalars().all()

    names: dict[str, str] = {}
    for r in reports:
        if r.reported_id not in names:
            profile = await db.get(Profile, r.reported_id)
            names[r.reported_id] = profile.display_name if profile else None
    return [
        AdminReportItem(
            id=r.id,
            reporter_id=r.reporter_id,
            reported_id=r.reported_id,
            reported_name=names[r.reported_id],
            reason=r.reason,
            details=r.details,
            status=r.status,
            created_at=r.created_at,
        )
        for r in reports
    ]


@router.post("/reports/{report_id}/resolve", response_model=AdminReportItem)
async def resolve_report(
    report_id: str,
    body: ResolveReportIn,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminReportItem:
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(404, "Signalement introuvable.")
    if body.resolution not in ("resolved", "dismissed"):
        raise HTTPException(400, "resolution attendue : 'resolved' ou 'dismissed'")
    report.status = body.resolution
    report.resolution = body.resolution
    report.resolved_at = utcnow()
    await db.commit()
    profile = await db.get(Profile, report.reported_id)
    return AdminReportItem(
        id=report.id,
        reporter_id=report.reporter_id,
        reported_id=report.reported_id,
        reported_name=profile.display_name if profile else None,
        reason=report.reason,
        details=report.details,
        status=report.status,
        created_at=report.created_at,
    )


@router.get("/users", response_model=list[AdminUserItem])
async def list_users(
    q: str | None = Query(None, description="Filtre téléphone ou nom"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AdminUserItem]:
    stmt = (
        select(User, Profile)
        .outerjoin(Profile, Profile.user_id == User.id)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(User.phone_e164.like(like), Profile.display_name.like(like))
        )
    rows = (await db.execute(stmt)).all()
    return [
        AdminUserItem(
            id=u.id,
            phone_e164=u.phone_e164,
            age=Profile.age_of(u.birthdate) if u.birthdate else None,
            role=u.role,
            is_active=u.is_active,
            is_verified=u.is_verified,
            display_name=p.display_name if p else None,
            city=p.city if p else None,
            created_at=u.created_at,
        )
        for u, p in rows
    ]


@router.patch("/users/{user_id}", response_model=AdminUserItem)
async def patch_user(
    user_id: str,
    body: AdminUserPatch,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserItem:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Utilisateur introuvable.")
    if user.id == admin.id and body.is_active is False:
        raise HTTPException(400, "Vous ne pouvez pas désactiver votre propre compte.")
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.role is not None:
        if body.role not in ("user", "admin"):
            raise HTTPException(400, "role attendu : 'user' ou 'admin'")
        user.role = body.role
    await db.commit()
    profile = await db.get(Profile, user_id)
    return AdminUserItem(
        id=user.id,
        phone_e164=user.phone_e164,
        age=Profile.age_of(user.birthdate),
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        display_name=profile.display_name if profile else None,
        city=profile.city if profile else None,
        created_at=user.created_at,
    )


@router.get("/photos", response_model=list[AdminPhotoItem])
async def list_photos(
    status_filter: str = Query("pending"),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AdminPhotoItem]:
    photos = (
        (
            await db.execute(
                select(ProfilePhoto)
                .where(ProfilePhoto.status == status_filter)
                .order_by(ProfilePhoto.created_at)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [
        AdminPhotoItem(
            id=p.id, user_id=p.user_id, url=p.url, status=p.status, created_at=p.created_at
        )
        for p in photos
    ]


@router.post("/photos/{photo_id}/moderate", response_model=AdminPhotoItem)
async def moderate_photo(
    photo_id: str,
    body: ModeratePhotoIn,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminPhotoItem:
    photo = await db.get(ProfilePhoto, photo_id)
    if photo is None:
        raise HTTPException(404, "Photo introuvable.")
    if body.action == "approve":
        photo.status = "approved"
    elif body.action == "reject":
        photo.status = "rejected"
        delete_profile_photo(photo.file_path)  # rejet = fichier supprimé
    else:
        raise HTTPException(400, "action attendue : 'approve' ou 'reject'")
    await db.commit()
    return AdminPhotoItem(
        id=photo.id,
        user_id=photo.user_id,
        url=photo.url,
        status=photo.status,
        created_at=photo.created_at,
    )
