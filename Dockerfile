# ─────────────────────────────────────────────────────────────
# DocSeva – production Dockerfile
# Multi-stage: builder installs deps; runtime is a slim image.
# ─────────────────────────────────────────────────────────────

# ── Stage 1: dependency builder ──────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY requirements/ ./requirements/
RUN pip install --prefix=/install -r requirements.txt

# ── Stage 2: production runtime ──────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

# Install runtime-only system libraries
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    # Create a non-root user for security
    && groupadd --system docseva \
    && useradd --system --gid docseva --no-create-home docseva

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source (excluding dev/build artefacts via .dockerignore)
COPY --chown=docseva:docseva . .

RUN chmod +x ./entrypoint.sh

# Volumes for persistent data outside the container image
VOLUME ["/app/media"]

USER docseva

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["sh", "-c", "gunicorn docseva.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers ${GUNICORN_WORKERS:-3} \
    --timeout ${GUNICORN_TIMEOUT:-60} \
    --max-requests ${GUNICORN_MAX_REQUESTS:-1200} \
    --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER:-200} \
    --access-logfile - \
    --error-logfile - \
    --log-level info"]
