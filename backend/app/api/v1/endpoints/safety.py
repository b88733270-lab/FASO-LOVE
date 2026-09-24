"""Sécurité sociale & compte : blocages, signalements, suppression/export.

La suppression de compte efface les données personnelles (conformité loi
010-2017/AN — droit à l'effacement) et révoque toutes les sessions.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.interactions import Block, Like, Match
from app.models.message import Message
from app.models.otp_code import OtpCode
from app.models.profile import Profile
from app.models.profile_photo import ProfilePhoto
from app.models.refresh_token import RefreshToken
from app.models.report import REPORT_REASONS, Report
from app.models.user import User
from app.schemas.safety import BlockIn, BlockOut, ReportIn, ReportOut
from app.services.media import delete_profile_photo
from app.services.matching import get_blocked_ids

router = APIRouter(tags=["sécurité & compte"])


# --------------------------------------------------------------- Blocages


@router.post("/blocks", response_model=BlockOut, status_code=201)
async def block_user(
    body: BlockIn,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BlockOut:
    if body.user_id == me.id:
        raise HTTPException(400, "Vous ne pouvez pas vous bloquer vous-même.")
    target = await db.get(User, body.user_id)
    if target is None:
        raise HTTPException(404, "Utilisateur introuvable.")

    existing = await db.scalar(
        select(Block).where(
            Block.blocker_id == me.id, Block.blocked_id == body.user_id
        )
    )
    if existing is None:
        existing = Block(blocker_id=me.id, blocked_id=body.user_id)
        db.add(existing)
        await db.commit()
    return BlockOut(user_id=existing.blocked_id, created_at=existing.created_at)


@router.delete("/blocks/{user_id}", status_code=204)
async def unblock_user(
    user_id: str,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    block = await db.scalar(
        select(Block).where(Block.blocker_id == me.id, Block.blocked_id == user_id)
    )
    if block is not None:
        await db.delete(block)
        await db.commit()
    return None


@router.get("/blocks", response_model=list[BlockOut])
async def my_blocks(
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BlockOut]:
    rows = (
        (await db.execute(select(Block).where(Block.blocker_id == me.id)))
        .scalars()
        .all()
    )
    return [BlockOut(user_id=b.blocked_id, created_at=b.created_at) for b in rows]


# ------------------------------------------------------------ Signalements


@router.post("/reports", response_model=ReportOut, status_code=201)
async def report_user(
    body: ReportIn,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportOut:
    if body.reported_user_id == me.id:
        raise HTTPException(400, "Vous ne pouvez pas vous signaler vous-même.")
    if body.reason not in REPORT_REASONS:
        raise HTTPException(
            400, f"Motif invalide (attendu : {', '.join(REPORT_REASONS)})"
        )
    target = await db.get(User, body.reported_user_id)
    if target is None:
        raise HTTPException(404, "Utilisateur introuvable.")

    report = Report(
        reporter_id=me.id,
        reported_id=body.reported_user_id,
        reason=body.reason,
        details=body.details,
    )
    db.add(report)
    await db.commit()
    return ReportOut(
        id=report.id,
        reported_user_id=report.reported_id,
        reason=report.reason,
        status=report.status,
    )


# ------------------------------------------------------ Suppression/export


@router.delete(
    "/users/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer définitivement mon compte et mes données",
)
async def delete_my_account(
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    # Suppression explicite des dépendances (portable SQLite/PostgreSQL),
    # puis du compte. Les fichiers physiques sont aussi supprimés.
    photos = (
        (await db.execute(select(ProfilePhoto).where(ProfilePhoto.user_id == me.id)))
        .scalars()
        .all()
    )
    for photo in photos:
        delete_profile_photo(photo.file_path)

    my_matches = select(Match.id).where(
        or_(Match.user_low == me.id, Match.user_high == me.id)
    )
    await db.execute(delete(Message).where(Message.match_id.in_(my_matches)))
    await db.execute(delete(Message).where(Message.sender_id == me.id))
    await db.execute(delete(Match).where(or_(Match.user_low == me.id, Match.user_high == me.id)))
    await db.execute(delete(Like).where(or_(Like.from_user_id == me.id, Like.to_user_id == me.id)))
    await db.execute(delete(Block).where(or_(Block.blocker_id == me.id, Block.blocked_id == me.id)))
    await db.execute(delete(Report).where(or_(Report.reporter_id == me.id, Report.reported_id == me.id)))
    await db.execute(delete(ProfilePhoto).where(ProfilePhoto.user_id == me.id))
    await db.execute(delete(Profile).where(Profile.user_id == me.id))
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == me.id))
    await db.execute(delete(OtpCode).where(OtpCode.phone_e164 == me.phone_e164))
    await db.delete(me)
    await db.commit()
    return None


@router.get("/users/me/export", summary="Exporter mes données (portabilité)")
async def export_my_data(
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile = await db.get(Profile, me.id)
    photos = (
        (await db.execute(select(ProfilePhoto).where(ProfilePhoto.user_id == me.id)))
        .scalars()
        .all()
    )
    matches = (
        (
            await db.execute(
                select(Match).where(
                    or_(Match.user_low == me.id, Match.user_high == me.id)
                )
            )
        )
        .scalars()
        .all()
    )
    messages = (
        (
            await db.execute(
                select(Message).where(Message.sender_id == me.id)
            )
        )
        .scalars()
        .all()
    )
    return {
        "compte": {
            "telephone": me.phone_e164,
            "date_naissance": me.birthdate.isoformat(),
            "cree_le": me.created_at.isoformat(),
        },
        "profil": (
            {
                "nom_affiche": profile.display_name,
                "genre": profile.gender,
                "recherche": profile.looking_for,
                "bio": profile.bio,
                "ville": profile.city,
                "interets": profile.interests,
            }
            if profile
            else None
        ),
        "photos": [p.url for p in photos],
        "matchs": [m.id for m in matches],
        "messages_envoyes": [
            {"match": m.match_id, "contenu": m.content, "date": m.created_at.isoformat()}
            for m in messages
        ],
    }
