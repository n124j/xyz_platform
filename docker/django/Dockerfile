# ──────────────────────────────────────────────────────────────
# XYZ Platform — Django Application Dockerfile
# Multi-stage build: builder installs dependencies,
#                    runtime creates minimal production image
# ──────────────────────────────────────────────────────────────

# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

ARG REQUIREMENTS=production

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
RUN pip install --prefix=/install -r requirements/${REQUIREMENTS}.txt

# Stage 2: Runtime image
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    APP_HOME=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd -r xyz && useradd -r -g xyz -d $APP_HOME -s /sbin/nologin xyz

WORKDIR $APP_HOME

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application
COPY --chown=xyz:xyz . .

# Create required directories
RUN mkdir -p logs media staticfiles && chown -R xyz:xyz .

USER xyz

# Collect static files
RUN python manage.py collectstatic --noinput --settings=config.settings.production || true

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/admin/login/ || exit 1

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "gthread", \
     "--threads", "2", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
