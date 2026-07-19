"""Production settings (Railway): TLS-terminating proxy in front of gunicorn."""

import os

from .base import *  # noqa: F401,F403

DEBUG = False

SECRET_KEY = os.environ["OHARA_SECRET_KEY"]

# Deployment host/origins come from the environment, not the repo.
ALLOWED_HOSTS = [
    host for host in os.environ.get("OHARA_ALLOWED_HOSTS", "").split(",") if host
]

CSRF_TRUSTED_ORIGINS = [
    origin
    for origin in os.environ.get("OHARA_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin
]

TIME_ZONE = "America/Bogota"

# Railway terminates TLS and forwards the original scheme in this header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

WHITENOISE_AUTOREFRESH = False
WHITENOISE_USE_FINDERS = False
