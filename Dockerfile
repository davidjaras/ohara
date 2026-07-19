# Single multi-stage Dockerfile for ohara.
#   - target "dev":  used by docker-compose; source is bind-mounted, runs runserver.
#   - target "prod": self-contained image for Railway; serves the built SPA
#     via WhiteNoise and runs migrations on boot (see CMD).

# ---------- frontend build (prod only) ----------
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- shared backend base ----------
FROM python:3.13-slim AS backend-base
ENV PYTHONUNBUFFERED=1 \
    # Keep the venv outside /app/backend so the dev bind mount never shadows it.
    UV_PROJECT_ENVIRONMENT=/opt/venv
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./

# ---------- development ----------
FROM backend-base AS dev
RUN uv sync --frozen
COPY backend/ ./
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---------- production (Railway) ----------
FROM backend-base AS prod
RUN uv sync --frozen --no-dev
COPY backend/ ./
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist
RUN uv run python manage.py compilemessages -l es \
    && uv run python manage.py collectstatic --no-input
# Migrations run on every boot so each Railway deploy is self-migrating.
CMD ["sh", "-c", "uv run python manage.py migrate --no-input && uv run gunicorn config.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 2"]
