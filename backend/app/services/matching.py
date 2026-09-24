"""Logique de découverte et de matching FASO LOVE.

Filtres appliqués :
1. compatibilité d'orientation **réciproque** (les deux préférences doivent
   correspondre) ;
2. tranche d'âge (âge calculé côté serveur) ;
3. exclusions : soi-même, profils déjà évalués (like/pass/coup de cœur),
   utilisateurs bloqués (dans les deux sens), comptes inactifs ;
4. une photo approuvée minimum (confiance du catalogue) ;
5. distance Haversine si les deux utilisateurs ont partagé leur position.

TODO(phase-3b, perfs) : basculer le tri géographique sur PostGIS dès que
le volume dépasse quelques milliers de profils par ville.
"""

import math

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interactions import Block, Like, Match, canonical_pair
from app.models.profile import Profile
from app.models.profile_photo import ProfilePhoto
from app.models.user import User

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance orthodromique en kilomètres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _orientation_clause(my: Profile) -> list:
    """Le profil candidat correspond à ma recherche…"""
    clauses = []
    if my.looking_for != "everyone":
        clauses.append(Profile.gender == my.looking_for)
    # …et je corresponds à LA sienne (réciprocité d'orientation).
    clauses.append(
        or_(
            Profile.looking_for == "everyone",
            Profile.looking_for == my.gender,
        )
    )
    return clauses


async def get_blocked_ids(db: AsyncSession, user_id: str) -> set[str]:
    """Utilisateurs bloqués par moi OU m'ayant bloqué."""
    rows = await db.execute(
        select(Block.blocker_id, Block.blocked_id).where(
            or_(Block.blocker_id == user_id, Block.blocked_id == user_id)
        )
    )
    blocked = set()
    for blocker, blocked_id in rows:
        blocked.add(blocked_id if blocker == user_id else blocker)
    return blocked


async def get_match_or_none(
    db: AsyncSession, match_id: str, user_id: str
) -> Match | None:
    """Charge un match si l'utilisateur en est membre (sinon None)."""
    match = await db.get(Match, match_id)
    if match is None or user_id not in (match.user_low, match.user_high):
        return None
    return match


async def discover_candidates(
    db: AsyncSession,
    me: User,
    my_profile: Profile,
    *,
    min_age: int,
    max_age: int,
    max_distance_km: float | None,
    limit: int,
) -> list[tuple[User, Profile, float | None]]:
    """Retourne [(user, profile, distance_km)] triés par distance."""
    evaluated = select(Like.to_user_id).where(Like.from_user_id == me.id)
    has_approved_photo = (
        select(func.count())
        .select_from(ProfilePhoto)
        .where(
            ProfilePhoto.user_id == Profile.user_id,
            ProfilePhoto.status == "approved",
        )
        .correlate(Profile)
        .scalar_subquery()
        > 0
    )

    blocked_ids = await get_blocked_ids(db, me.id)
    if blocked_ids:
        excl_capture = list(blocked_ids) + [me.id]
    else:
        excl_capture = [me.id]

    stmt = (
        select(User, Profile)
        .join(Profile, Profile.user_id == User.id)
        .where(
            User.is_active.is_(True),
            User.is_verified.is_(True),
            User.id.not_in(excl_capture),
            User.id.not_in(evaluated),
            has_approved_photo,
            *_orientation_clause(my_profile),
        )
    )
    rows = (await db.execute(stmt)).all()

    candidates: list[tuple[User, Profile, float | None]] = []
    for user, profile in rows:
        age = Profile.age_of(user.birthdate)
        if not (min_age <= age <= max_age):
            continue
        distance: float | None = None
        if (
            my_profile.latitude is not None
            and my_profile.longitude is not None
            and profile.latitude is not None
            and profile.longitude is not None
        ):
            distance = haversine_km(
                my_profile.latitude,
                my_profile.longitude,
                profile.latitude,
                profile.longitude,
            )
        if max_distance_km is not None and (
            distance is None or distance > max_distance_km
        ):
            continue
        candidates.append((user, profile, distance))

    # Tri : distance d'abord (les « sans position » à la fin), puis nouveauté.
    candidates.sort(
        key=lambda t: (
            math.inf if t[2] is None else t[2],
            -t[0].created_at.timestamp(),
        )
    )
    return candidates[:limit]


async def register_reaction(
    db: AsyncSession, me: User, target_id: str, action: str
) -> tuple[Like, Match | None]:
    """Enregistre un like/pass/coup de cœur.

    - Idempotent : une seule réaction par (moi, cible) ;
    - Si la cible m'a déjà liké positivement et que ma réaction est
      positive → création du match (une seule fois, paire canonique).

    Retourne (réaction, match créé ou None).
    """
    from fastapi import HTTPException

    if target_id == me.id:
        raise HTTPException(400, "Vous ne pouvez pas réagir à votre propre profil.")

    blocked = await get_blocked_ids(db, me.id)
    if target_id in blocked:
        raise HTTPException(403, "Interaction impossible avec cet utilisateur.")

    target = await db.get(User, target_id)
    if target is None or not target.is_active:
        raise HTTPException(404, "Profil introuvable.")

    existing = await db.scalar(
        select(Like).where(
            Like.from_user_id == me.id, Like.to_user_id == target_id
        )
    )
    if existing is not None:
        # Déjà évalué : on retourne l'état actuel sans rien recréer.
        low, high = canonical_pair(me.id, target_id)
        match = await db.scalar(
            select(Match).where(Match.user_low == low, Match.user_high == high)
        )
        return existing, match

    like = Like(from_user_id=me.id, to_user_id=target_id, action=action)
    db.add(like)

    match: Match | None = None
    if action in ("like", "super_like"):
        reciprocal = await db.scalar(
            select(Like).where(
                Like.from_user_id == target_id,
                Like.to_user_id == me.id,
                Like.action.in_(("like", "super_like")),
            )
        )
        if reciprocal is not None:
            low, high = canonical_pair(me.id, target_id)
            match = await db.scalar(
                select(Match).where(
                    and_(Match.user_low == low, Match.user_high == high)
                )
            )
            if match is None:
                match = Match(user_low=low, user_high=high)
                db.add(match)
                await db.flush()

    await db.commit()
    return like, match
