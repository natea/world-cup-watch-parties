"""
Django settings for the World Cup 2026 watch-party finder.

Database is env-driven: PostgreSQL in production (the family-friendly DB
predicate is verified there), SQLite for zero-setup local dev. Set
`DATABASE_URL` (postgres://...) to use PostgreSQL; otherwise a local SQLite
file is used.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key-change-in-prod")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"
).split(",")

# Render injects the service's external hostname at runtime; trust it so the
# default onrender.com URL works without hardcoding it.
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# CSRF for the Django admin / browsable API when served over HTTPS in prod.
CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o
]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "events",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves Django's collected static files (admin, DRF) in prod,
    # right after SecurityMiddleware per WhiteNoise docs.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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


def _database_config() -> dict:
    """Parse DATABASE_URL (postgres://) or fall back to a local SQLite file."""
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("postgres://") or url.startswith("postgresql://"):
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username or "",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
        }
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }


DATABASES = {"default": _database_config()}

# Reuse DB connections across requests (avoids a fresh connect per request,
# which is a big chunk of latency against a managed Postgres). Harmless on
# SQLite. Health-check stale connections before reuse (Django ≥4.1).
DATABASES["default"]["CONN_MAX_AGE"] = int(os.environ.get("DJANGO_CONN_MAX_AGE", "600"))
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

# True when running on PostgreSQL, where the DB-level family_friendly filter is
# supported. Views consult this to choose the Python-predicate fallback on SQLite.
USING_POSTGRES = DATABASES["default"]["ENGINE"].endswith("postgresql")

# Production HTTPS hardening. Skipped in dev so plain-HTTP localhost works.
# Render terminates TLS at its proxy and forwards X-Forwarded-Proto, which the
# proxy header below lets Django trust when deciding a request is secure.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 days
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True  # store UTC, render local on the client

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# In production WhiteNoise serves a hashed, compressed manifest of collected
# static files. In dev (DEBUG) we keep Django's default storage so `runserver`
# serves admin/DRF assets straight from the source tree — no collectstatic, no
# "Missing staticfiles manifest entry" errors.
if not DEBUG:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

# CORS: allow the Vite dev origin to call the API during development.
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")
