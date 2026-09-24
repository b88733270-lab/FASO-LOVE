"""Endpoints de santé (supervision, healthchecks Docker/CI, probes k8s)."""

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.core.config import get_settings
from app.core.deps import get_db

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


@router.get("/health/live")
async def liveness() -> dict:
    """Probe balle : le process répond. Redémarrer si KO permanent."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness(db=Depends(get_db)) -> dict | None:
    """Probe de préparation : DB rejointe → accepter du trafic."""
    await db.execute(text("SELECT 1"))
    return {"status": "ready"}

