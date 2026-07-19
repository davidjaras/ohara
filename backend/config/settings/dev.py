"""Development settings: docker-compose, host-side pytest and manage.py runs."""

import os

from .base import *  # noqa: F401,F403

DEBUG = True

SECRET_KEY = os.environ.get(
    "OHARA_SECRET_KEY",
    "django-insecure-dev-only-key-cambiar-en-produccion",
)

# The SPA is served by Vite on :5173 and proxies to Django, so cross-origin
# POSTs (login form, API writes) need to be trusted.
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "OHARA_CSRF_TRUSTED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

# Password-reset emails: printed to the runserver console.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Serve static files straight from the filesystem (no collectstatic).
WHITENOISE_AUTOREFRESH = True
WHITENOISE_USE_FINDERS = True
