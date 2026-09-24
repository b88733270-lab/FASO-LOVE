"""Endpoint de santé (supervision, healthchecks Docker/CI)."""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["santé"])


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "env": settings.env,
    }
