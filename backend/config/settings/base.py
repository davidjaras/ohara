"""Shared Django settings for ohara.

Environment-specific values live in dev.py / prod.py; sensitive values come
from OHARA_* variables and the database from DATABASE_URL.
"""

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent

ALLOWED_HOSTS = os.environ.get("OHARA_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "tracker",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"

# The built frontend (frontend/dist) is served by Django in production.
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates", FRONTEND_DIST],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Postgres everywhere: docker-compose provides DATABASE_URL in containers,
# and the default targets the compose db's published port for host-side runs
# (e.g. pytest outside Docker).
DATABASES = {
    "default": dj_database_url.config(
        default="postgres://ohara:ohara@localhost:5432/ohara",
        conn_max_age=600,
    )
}


def _system_timezone() -> str:
    """System timezone (/etc/localtime symlink on macOS/Linux)."""
    try:
        link = os.readlink("/etc/localtime")
        if "zoneinfo/" in link:
            return link.split("zoneinfo/")[-1]
    except OSError:
        pass
    return "UTC"


LANGUAGE_CODE = "es"
LANGUAGES = [
    ("es", "Español"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = os.environ.get("OHARA_TIME_ZONE", _system_timezone())
USE_I18N = True
USE_TZ = True

# Authentication (Django's native session auth).
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

DEFAULT_FROM_EMAIL = os.environ.get("OHARA_FROM_EMAIL", "ohara@localhost")

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
WHITENOISE_ROOT = FRONTEND_DIST if FRONTEND_DIST.exists() else None

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# Domain configuration.
KIND_SESSION = "session"
KIND_MEASUREMENT = "measurement"

DEFAULT_SESSION_METRIC = "estudio"
DEFAULT_SESSION_LIMIT = 50
DEFAULT_MEASUREMENT_LIMIT = 100
DEFAULT_STATS_DAYS = 14
DEFAULT_STATS_WEEKS = 12

METRICS = {
    "estudio": {
        "key": "estudio",
        "name": "Estudio",
        "kind": KIND_SESSION,
        "unit": "min",
        "default_weekly_goal_minutes": 270,
    },
    "peso": {
        "key": "peso",
        "name": "Peso",
        "kind": KIND_MEASUREMENT,
        "unit": "kg",
    },
}

# Selectable accent colors for the per-user theme. The visual values live in the
# frontend (index.css); the backend only stores which one the user picked.
ACCENT_COLORS = ["blue", "green", "teal", "violet", "rose", "amber", "coral"]
DEFAULT_ACCENT_COLOR = "blue"
