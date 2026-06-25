"""XYZ Platform — Development Settings"""

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS += [  # noqa: F405
    "debug_toolbar",
    "django_extensions",
]

MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE  # noqa: F405

INTERNAL_IPS = ["127.0.0.1"]

# Use console email backend in development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Relax CORS for local dev
CORS_ALLOW_ALL_ORIGINS = True

# CSRF trusted origins (required for Django 4.0+ when using non-standard ports)
CSRF_TRUSTED_ORIGINS = ["http://localhost:3002", "http://127.0.0.1:3002"]

# Use basic static storage in development (avoids manifest issues with Dash)
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
