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
    # Phase 10 — traçage des exceptions en production (Sentry), branché par
    # simple présence du DSN dans le vault ; import tolerable au SDK absent.
    if settings.sentry_dsn:
        try:
            import sentry_sdk

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                environment=settings.sentry_environment or settings.env,
                traces_sample_rate=0.1,
                send_default_pii=False,  # jamais de données personnelles
            )
        except ImportError:
            import logging

            logging.getLogger("fasolove.startup").warning(
                "SENTRY_DSN défini mais sentry-sdk non installé — `pip install "
                "sentry-sdk[fastapi]` sur le serveur."
            )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "API de la plateforme de rencontre **FASO LOVE** (Burkina Faso, "
            "strictement 18+). Authentification par numéro de téléphone +226 "
            "avec code OTP SMS, sessions JWT avec rotation, limitation de débit."
        ),
        # Phase 9 — en production, ni doc interactive ni schéma OpenAPI
        # exposés (surface d'attaque minimale ; le runbook documente tout).
        docs_url=None if settings.env == "prod" else "/docs",
        redoc_url=None,
        openapi_url=None if settings.env == "prod" else "/openapi.json",
    )

    # Phase 9 — garde-fou de configuration au démarrage : en prod, n'importe
    # quelle variable laissée sur sa valeur DEV est un trou de sécurité.
    if settings.env == "prod":
        alerts = []
        if "change-me" in settings.jwt_secret:
            alerts.append("JWT_SECRET est la valeur de développement")
        if settings.cors_origins.strip() in ("*", ""):
            alerts.append("CORS_ORIGINS ouvert à '*'")
        if settings.sms_provider == "console":
            alerts.append("SMS_PROVIDER=console (aucun vrai SMS)")
        if getattr(settings, "otp_dev_echo", False):
            alerts.append("OTP_DEV_ECHO actif (les codes sont renvoyés en réponse)")
        if settings.payments_simulation_enabled:
            alerts.append("PAYMENTS_SIMULATION_ENABLED actif (fausses confirmations)")
        if settings.payments_provider == "mock":
            alerts.append("PAYMENTS_PROVIDER=mock (aucun vrai encaissement)")
        if settings.push_provider == "log" and not settings.fcm_server_key:
            alerts.append("PUSH log sans FCM_SERVER_KEY")
        if alerts:
            import logging

            logging.getLogger("fasolove.startup").warning(
                "⚠️  CONFIGURATION PROD NON SÛRE : %s", "; ".join(alerts)
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
        # Phase 9 — durcissement : pas d'accès navigateur aux capteurs /
        # aux caméras ; HSTS uniquement quand l'API est servie en HTTPS
        # (prod derrière le reverse proxy) — jamais sur localhost dev.
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), camera=(), microphone=(), payment=(), usb=()",
        )
        if settings.env == "prod":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=15552000; includeSubDomains",
            )
        # Données sensibles (auth, compte, monétisation) : jamais de cache.
        if request.url.path.startswith(
            ("/api/v1/auth", "/api/v1/users", "/api/v1/subscriptions")
        ):
            response.headers.setdefault("Cache-Control", "no-store")
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
