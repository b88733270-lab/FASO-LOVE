# ============================================================================
# FASO LOVE API — image de production (Phase 10)
#
#   docker build -t fasolove-api ./backend
#   docker run --env-file .env -p 8000:8000 fasolove-api
#
# Voir infra/docker-compose.prod.yml pour le déploiement omplet
# (api + PostgreSQL + reverse proxy TLS).
# ============================================================================

FROM python:3.11-slim

# Utilisateur non-root obligatoire (checklist sécurité Phase 9).
RUN useradd --create-home --shell /sbin/nologin fasolove

WORKDIR /app

# Dépendances : couche cachée seule (requirements rarement modifiés).
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Code applicatif.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# Médias persistants (montés en volume — voir compose).
RUN mkdir -p /app/media && chown -R fasolove:fasolove /app
USER fasolove

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=4)" || exit 1

# Entrypoint : migrations à jour, puis serveur (workers guidés par l'host).
ENV UVICORN_WORKERS=1
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS}"]
