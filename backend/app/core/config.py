"""Configuration centrale de l'API FASO LOVE.

Toutes les variables sont surchargeables par l'environnement (ou `.env`).
⚠️ Aucun secret en dur ici : les valeurs sensibles viennent de l'environnement.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Application
    app_name: str = "FASO LOVE API"
    app_version: str = "0.1.0"
    env: str = "dev"  # dev | staging | prod
    api_v1_prefix: str = "/api/v1"

    # Base de données (async). PostgreSQL en recette/prod ; SQLite acceptée
    # en test unitaire (override de dépendance).
    database_url: str = (
        "postgresql+asyncpg://fasolove:fasolove@localhost:5432/fasolove"
    )

    # JWT
    jwt_secret: str = "change-me-en-production-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # OTP (inscription/connexion par numéro de téléphone +226)
    otp_length: int = 6
    otp_ttl_minutes: int = 5
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60
    # Limites anti-abus OTP (assouplies en dev/preview via l'environnement).
    otp_request_rate_limit: str = "3/minute"
    otp_verify_rate_limit: str = "10/minute"
    # ⚠️ DEV uniquement : renvoyer le code OTP dans la réponse HTTP.
    otp_dev_echo: bool = False

    # Envoi SMS : "console" en dev (le code est affiché dans les logs).
    # Phase 1b : adaptateurs réels (Africa's Talking, Orange SMS API…).
    sms_provider: str = "console"

    # Règle d'âge — application strictement réservée aux adultes.
    min_age: int = 18
    max_age: int = 120

    # CORS (restreindre en production — voir plan, phase 6).
    cors_origins: str = "*"

    # Médias (photos de profil)
    media_dir: str = "./media"  # phase 2b : stockage objet S3/MinIO
    media_max_upload_mb: int = 10
    media_max_photos_per_user: int = 6
    # true en dev uniquement : photos approuvées sans validation manuelle.
    media_auto_approve: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
