"""Django settings for ohara.

App personal de un solo usuario, local-first. Los valores sensibles o de
entorno se toman de variables OHARA_* con defaults pensados para desarrollo.
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

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "tracker",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

# El frontend compilado (frontend/dist) se sirve desde Django en producción.
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [FRONTEND_DIST],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
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
    """Zona horaria del sistema (symlink /etc/localtime en macOS/Linux)."""
    try:
        link = os.readlink("/etc/localtime")
        if "zoneinfo/" in link:
            return link.split("zoneinfo/")[-1]
    except OSError:
        pass
    return "UTC"


LANGUAGE_CODE = "es"
TIME_ZONE = os.environ.get("OHARA_TIME_ZONE", _system_timezone())
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
WHITENOISE_ROOT = FRONTEND_DIST if FRONTEND_DIST.exists() else None
# En desarrollo whitenoise sirve directo del filesystem (sin collectstatic).
WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_USE_FINDERS = DEBUG

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "UNAUTHENTICATED_USER": None,
}
