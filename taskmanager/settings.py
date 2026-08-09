"""
Django settings for taskmanager project.
Configured to run locally (SQLite) and in production on Railway
(Postgres, via DATABASE_URL) with minimal changes.
"""

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# --------------------------------------------------------------------
# Core / security
# --------------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-dev-only-change-me")

DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

# Railway provides RAILWAY_STATIC_URL / RAILWAY_PUBLIC_DOMAIN at runtime.
_allowed = os.environ.get("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in _allowed.split(",") if h.strip()] or ["*"]

_railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
if _railway_domain and _railway_domain not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_railway_domain)

CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if h != "*"]

# --------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3rd party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    # local
    "accounts",
    "projects",
    "tasks",
    "submissions",
    "chat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "taskmanager.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "taskmanager.wsgi.application"

# --------------------------------------------------------------------
# Database
# --------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=True)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# --------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

# Private code required to self-register as an admin (see accounts/serializers.py).
# Leave unset/blank to disable self-service admin signup entirely -- in that
# case every new signup is a member, and admins can only be created via
# `manage.py createsuperuser`, `manage.py promote_admin <username>`, or by
# an existing admin/superuser editing the user's role in /admin/.
ADMIN_SIGNUP_CODE = os.environ.get("ADMIN_SIGNUP_CODE", "").strip()

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------
# DRF / JWT
# --------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=6),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# --------------------------------------------------------------------
# CORS -- open by default so any frontend can hit the API;
# tighten via CORS_ALLOWED_ORIGINS env var in production if desired.
# --------------------------------------------------------------------
_cors_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "")
if _cors_origins:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins.split(",") if o.strip()]
else:
    CORS_ALLOW_ALL_ORIGINS = True

# --------------------------------------------------------------------
# I18N
# --------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------
# Static files (WhiteNoise serves these directly from Gunicorn)
# --------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# --------------------------------------------------------------------
# Media (user-uploaded submission files, up to 1GB)
# Stored on local disk. NOTE: Railway's filesystem is ephemeral --
# uploaded files will be lost on redeploy/restart. For durable
# production storage, swap this for a service like AWS S3 (e.g. via
# django-storages) and point MEDIA_URL/DEFAULT_FILE_STORAGE at it.
# --------------------------------------------------------------------
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Allow large multipart request bodies (file uploads up to ~1GB).
# Actual per-file size is enforced in the submissions serializer/model.
DATA_UPLOAD_MAX_MEMORY_SIZE = None
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # switch to temp-file storage above 10MB

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# When Railway terminates TLS in front of the app, trust the forwarded proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() == "true"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
