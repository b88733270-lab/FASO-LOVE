"""Agrégateur des routes API v1."""

from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, chat, discover, health, profiles, safety

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(profiles.router)
api_router.include_router(discover.router)
api_router.include_router(chat.router)
api_router.include_router(safety.router)
api_router.include_router(admin.router)
