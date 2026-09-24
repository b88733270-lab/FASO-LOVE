"""Endpoints découverte & matching : file de profils, réactions, matchs."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.profiles import to_public
from app.core.deps import get_current_user, get_db
from app.core.rate_limit import limiter
from app.models.interactions import LIKE_ACTIONS, Block, Match
from app.models.message import Message
from app.models.profile import Profile
from app.models.profile_photo import ProfilePhoto
from app.models.user import User
from app.schemas.profiles import (
    MatchOut,
    MessageOut,
    PeerSummary,
    ProfilePublic,
    ReactionIn,
    ReactionOut,
)
from app.services.matching import (
    discover_candidates,
    get_blocked_ids,
    register_reaction,
)
from app.services.payments import QuotaExceeded, assert_reaction_quota

router = APIRouter(tags=["découverte & matchs"])


async def _require_my_profile(me: User, db: AsyncSession) -> Profile:
    profile = await db.get(Profile, me.id)
    if profile is None:
        raise HTTPException(
            400,
            "Complétez votre profil (nom, genre, photo) avant de découvrir "
            "d'autres profils.",
        )
    return profile


@router.get(
    "/discover",
    response_model=list[ProfilePublic],
    summary="File de profils à découvrir (géolocalisée, filtrée)",
)
@limiter.limit("60/minute")
async def discover(
    request: Request,
    min_age: int = Query(18, ge=18),
    max_age: int = Query(60, le=99),
    max_distance_km: float | None = Query(None, gt=0, le=1000),
    limit: int = Query(20, ge=1, le=50),
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProfilePublic]:
    my_profile = await _require_my_profile(me, db)
    candidates = await discover_candidates(
        db,
        me,
        my_profile,
        min_age=min_age,
        max_age=max_age,
        max_distance_km=max_distance_km,
        limit=limit,
    )
    cards: list[ProfilePublic] = []
    for user, profile, distance in candidates:
        photos = list(
            (
                await db.execute(
                    select(ProfilePhoto).where(
                        ProfilePhoto.user_id == user.id,
                        ProfilePhoto.status == "approved",
                    )
                )
            ).scalars()
        )
        cards.append(to_public(user, profile, photos, distance))
    return cards


@router.post(
    "/discover/react",
    response_model=ReactionOut,
    summary="Aimer / passer / coup de cœur sur un profil",
)
@limiter.limit("120/minute")
async def react(
    request: Request,
    body: ReactionIn,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReactionOut:
    if body.action not in LIKE_ACTIONS:
        raise HTTPException(400, f"Action invalide (attendu : {', '.join(LIKE_ACTIONS)})")
    await _require_my_profile(me, db)

    # Quota FREEMIUM du jour (Phase 7) — Premium = illimité.
    try:
        await assert_reaction_quota(db, me.id, body.action)
    except QuotaExceeded as exc:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Quota quotidien atteint. Passez à FASO LOVE Premium pour des "
            "likes illimités (Orange Money / Moov Money).",
        ) from exc

    _, match = await register_reaction(db, me, body.target_user_id, body.action)

    if match is not None:
        # Phase 8 — notification in-app + push aux DEUX membres du match.
        from app.services.notifications import notify_match_created

        await notify_match_created(db, match)
        return ReactionOut(
            matched=True,
            match_id=match.id,
            detail="Nouveau match ! 🎉",
            message="C'est un match ! Vous pouvez maintenant discuter.",
        )
    return ReactionOut(matched=False)


@router.get(
    "/matches",
    response_model=list[MatchOut],
    summary="Mes matchs (avec dernier message et non-lus)",
)
async def my_matches(
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MatchOut]:
    blocked = await get_blocked_ids(db, me.id)
    matches = (
        (
            await db.execute(
                select(Match)
                .where(or_(Match.user_low == me.id, Match.user_high == me.id))
                .order_by(Match.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    out: list[MatchOut] = []
    for match in matches:
        peer_id = match.other_user_id(me.id)
        if peer_id in blocked:
            continue  # un blocage coupe l'affichage du match
        peer = await db.get(User, peer_id)
        peer_profile = await db.get(Profile, peer_id)
        if peer is None or not peer.is_active or peer_profile is None:
            continue

        photo_url = await db.scalar(
            select(ProfilePhoto.file_path)
            .where(
                ProfilePhoto.user_id == peer_id,
                ProfilePhoto.status == "approved",
            )
            .order_by(ProfilePhoto.created_at)
            .limit(1)
        )

        last = await db.scalar(
            select(Message)
            .where(Message.match_id == match.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        unread = await db.scalar(
            select(func.count())
            .select_from(Message)
            .where(
                Message.match_id == match.id,
                Message.sender_id != me.id,
                Message.read_at.is_(None),
            )
        )

        out.append(
            MatchOut(
                match_id=match.id,
                created_at=match.created_at,
                peer=PeerSummary(
                    user_id=peer.id,
                    display_name=peer_profile.display_name,
                    age=Profile.age_of(peer.birthdate),
                    city=peer_profile.city,
                    photo_url=f"/media/{photo_url}" if photo_url else None,
                    interests=peer_profile.interests or [],
                ),
                last_message=(
                    MessageOut(
                        id=last.id,
                        sender_id=last.sender_id,
                        content=last.content,
                        created_at=last.created_at,
                        read_at=last.read_at,
                        is_mine=last.sender_id == me.id,
                    )
                    if last
                    else None
                ),
                unread_count=int(unread or 0),
            )
        )
    return out
