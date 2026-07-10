# ──────────────────────────────────────────────────────────────────────────────
# nut_Meals Infra Service — Multi-arch Dockerfile (linux/amd64 + linux/arm64)
# ──────────────────────────────────────────────────────────────────────────────

# ── Stage 1: dependency builder ──────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

# Build args for TARGETARCH / TARGETPLATFORM injected by BuildKit
ARG TARGETPLATFORM
ARG TARGETARCH
ARG BUILDPLATFORM

# System deps needed to compile Python packages with C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        libssl-dev \
        libffi-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy only requirements first — maximise layer cache hits
COPY requirements.txt .

RUN pip install --upgrade pip wheel setuptools \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# ── Stage 2: production image ─────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS production

ARG APP_VERSION=unknown
ARG GIT_SHA=unknown
ARG TARGETARCH

LABEL org.opencontainers.image.title="nut_Meals Infra Service" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.source="https://github.com/nut-meals/infra-service" \
      org.opencontainers.image.licenses="Proprietary"

# Runtime system deps: postgresql-client for pg_dump/pg_restore
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        postgresql-client \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Install pre-built wheels from builder
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl \
    && rm -rf /wheels

# Copy application source
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser migrations/ ./migrations/
COPY --chown=appuser:appuser scripts/ ./scripts/

# Make scripts executable
RUN chmod +x scripts/backup/*.sh scripts/recovery/*.sh 2>/dev/null || true

ENV APP_VERSION=${APP_VERSION} \
    GIT_SHA=${GIT_SHA} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]


# ── Stage 3: Celery worker (same image, different CMD) ────────────────────────
FROM production AS celery-worker

CMD ["celery", "-A", "app.services.celery_app:celery_app", "worker", \
     "--loglevel=info", "--concurrency=4", "-Q", "infra,backup,restore"]


# ── Stage 4: Celery beat scheduler ───────────────────────────────────────────
FROM production AS celery-beat

CMD ["celery", "-A", "app.services.celery_app:celery_app", "beat", \
     "--loglevel=info", "--scheduler=celery.beat:PersistentScheduler"]
