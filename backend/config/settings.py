"""Django settings for ohara.

Single-user, local-first personal app. Sensitive/environment values come
from OHARA_* variables with development-friendly defaults.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "OHARA_SECRET_KEY",
    "django-insecure-dev-only-key-cambiar-en-produccion",
)

DEBUG = os.environ.get("OHARA_DEBUG", "1") == "1"

ALLOWED_HOSTS = os.environ.get("OHARA_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# In development the SPA is served by Vite on :5173 and proxies to Django,
# so cross-origin POSTs (login form, API writes) need to be trusted.
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "OHARA_CSRF_TRUSTED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173" if DEBUG else "",
).split(",")
CSRF_TRUSTED_ORIGINS = [origin for origin in CSRF_TRUSTED_ORIGINS if origin]

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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("OHARA_DB_PATH", BASE_DIR / "db.sqlite3"),
    }
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

# Password-reset emails: printed to the console in development.
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get("OHARA_FROM_EMAIL", "ohara@localhost")

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
WHITENOISE_ROOT = FRONTEND_DIST if FRONTEND_DIST.exists() else None
# In development whitenoise serves straight from the filesystem (no collectstatic).
WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_USE_FINDERS = DEBUG

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
