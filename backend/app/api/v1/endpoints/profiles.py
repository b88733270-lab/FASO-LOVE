"""Endpoints profils : création/édition, consultation, photos modérées."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user, get_db
from app.models.profile import Profile
from app.models.profile_photo import ProfilePhoto
from app.models.user import User
from app.schemas.profiles import PhotoOut, ProfileIn, ProfileMine, ProfilePublic
from app.services.media import MediaError, delete_profile_photo, save_profile_photo

router = APIRouter(prefix="/profiles", tags=["profils"])

# Catalogue de centres d'intérêt (français, culture locale incluse).
INTERESTS_CATALOG = [
    "Cuisine", "Musique", "Danse", "Football", "Cinéma", "Lecture",
    "Voyage", "Mode", "Tech", "Nature", "Sport", "Théâtre", "Photo",
    "Écriture", "Langues", "Artisanat", "Moto", "Jardinage", "Jeux",
    "Bénévolat",
]


def _photo_out(photo: ProfilePhoto) -> PhotoOut:
    return PhotoOut(id=photo.id, url=photo.url, status=photo.status)


async def _photos_of(
    db: AsyncSession, user_id: str, *, approved_only: bool
) -> list[ProfilePhoto]:
    stmt = (
        select(ProfilePhoto)
        .where(ProfilePhoto.user_id == user_id)
        .order_by(ProfilePhoto.created_at)
    )
    if approved_only:
        stmt = stmt.where(ProfilePhoto.status == "approved")
    return list((await db.execute(stmt)).scalars())


def to_public(
    user: User,
    profile: Profile,
    photos: list[ProfilePhoto],
    distance_km: float | None = None,
) -> ProfilePublic:
    return ProfilePublic(
        user_id=user.id,
        display_name=profile.display_name,
        gender=profile.gender,
        age=Profile.age_of(user.birthdate),
        bio=profile.bio,
        city=profile.city,
        interests=profile.interests or [],
        photos=[_photo_out(p) for p in photos],
        distance_km=(
            round(distance_km, 1) if distance_km is not None else None
        ),
    )


@router.get("/catalog/interests", summary="Catalogue des centres d'intérêt")
async def interests_catalog() -> dict:
    return {"interests": INTERESTS_CATALOG}


@router.put("/me", response_model=ProfileMine, summary="Créer/mettre à jour mon profil")
async def upsert_my_profile(
    body: ProfileIn,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileMine:
    profile = await db.get(Profile, me.id)
    if profile is None:
        profile = Profile(user_id=me.id, display_name=body.display_name, gender=body.gender)
        db.add(profile)
    profile.display_name = body.display_name
    profile.gender = body.gender
    profile.looking_for = body.looking_for
    profile.bio = body.bio
    profile.city = body.city
    profile.interests = body.interests
    profile.latitude = body.latitude
    profile.longitude = body.longitude
    await db.commit()

    photos = await _photos_of(db, me.id, approved_only=False)
    return ProfileMine(
        **to_public(me, profile, photos).model_dump(),
        looking_for=profile.looking_for,
        latitude=profile.latitude,
        longitude=profile.longitude,
        updated_at=profile.updated_at,
    )


@router.get("/me", response_model=ProfileMine, summary="Mon profil")
async def get_my_profile(
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileMine:
    profile = await db.get(Profile, me.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil non créé. Complétez votre profil d'abord.",
        )
    photos = await _photos_of(db, me.id, approved_only=False)
    return ProfileMine(
        **to_public(me, profile, photos).model_dump(),
        looking_for=profile.looking_for,
        latitude=profile.latitude,
        longitude=profile.longitude,
        updated_at=profile.updated_at,
    )


@router.get("/{user_id}", response_model=ProfilePublic, summary="Profil public")
async def get_public_profile(
    user_id: str,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfilePublic:
    from app.services.matching import get_blocked_ids

    if me.id != user_id and user_id in await get_blocked_ids(db, me.id):
        raise HTTPException(404, "Profil introuvable.")
    user = await db.get(User, user_id)
    profile = await db.get(Profile, user_id)
    if user is None or not user.is_active or profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profil introuvable."
        )
    photos = await _photos_of(db, user_id, approved_only=True)
    return to_public(user, profile, photos)


@router.post(
    "/me/photos",
    response_model=PhotoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une photo (modérée)",
)
async def upload_photo(
    file: UploadFile = File(...),
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PhotoOut:
    settings = get_settings()
    profile = await db.get(Profile, me.id)
    if profile is None:
        raise HTTPException(
            400, "Créez votre profil avant d'ajouter des photos."
        )

    existing = await _photos_of(db, me.id, approved_only=False)
    active = [p for p in existing if p.status != "rejected"]
    if len(active) >= settings.media_max_photos_per_user:
        raise HTTPException(
            409,
            f"Maximum {settings.media_max_photos_per_user} photos par profil.",
        )

    data = await file.read()
    try:
        rel_path = save_profile_photo(me.id, data)
    except MediaError as exc:
        raise HTTPException(422, str(exc)) from exc

    photo = ProfilePhoto(
        user_id=me.id,
        file_path=rel_path,
        status="approved" if settings.media_auto_approve else "pending",
    )
    db.add(photo)
    await db.commit()
    return _photo_out(photo)


@router.delete(
    "/me/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une de mes photos",
)
async def delete_photo(
    photo_id: str,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    photo = await db.get(ProfilePhoto, photo_id)
    if photo is None or photo.user_id != me.id:
        raise HTTPException(404, "Photo introuvable.")
    delete_profile_photo(photo.file_path)
    await db.delete(photo)
    await db.commit()
    return None
