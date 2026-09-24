"""Point d'entrée de l'API FASO LOVE (FastAPI).

Lancer en dev : `uvicorn app.main:app --reload`
Documentation interactive : http://localhost:8000/docs
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.rate_limit import limiter

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "API de la plateforme de rencontre **FASO LOVE** (Burkina Faso, "
            "strictement 18+). Authentification par numéro de téléphone +226 "
            "avec code OTP SMS, sessions JWT avec rotation, limitation de débit."
        ),
        docs_url="/docs",
        redoc_url=None,
    )

    # Limitation de débit (anti-spam OTP, anti-bruteforce).
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(
        request: Request, exc: RateLimitExceeded
    ) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Trop de requêtes. Veuillez réessayer dans un instant."
            },
        )

    # CORS — à restreindre strictement en production (phase 6).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # En-têtes de sécurité (phase 6) — appliqués à toutes les réponses.
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        # Images publiques (profils) : lecture cross-origin autorisée pour
        # les clients CanvasKit de Flutter Web (console admin).
        if request.url.path.startswith("/media/"):
            response.headers.setdefault("Access-Control-Allow-Origin", "*")
        return response

    # Fichiers médias (photos compressées sans EXIF).
    # Phase 6 : URLs signées/hébergement objet + CDN.
    media_root = Path(settings.media_dir)
    media_root.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/media", StaticFiles(directory=media_root), name="media"
    )

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
        }

    return app


app = create_app()
