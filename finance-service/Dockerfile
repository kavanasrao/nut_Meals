# syntax=docker/dockerfile:1.7
# Multi-stage Dockerfile for the Finance service.
# Built multi-arch (linux/amd64, linux/arm64) via the GitHub Actions workflow
# using `docker buildx build --platform linux/amd64,linux/arm64`.

# ---- Stage 1: build dependencies into a wheel cache ----
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ---- Stage 2: runtime image ----
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="nut_meals-finance-service" \
      org.opencontainers.image.description="Double-entry ledger, reporting, and settlement reconciliation service" \
      org.opencontainers.image.vendor="nut_Meals"

# Non-root user for defense-in-depth
RUN groupadd --gid 1000 finance && \
    useradd --uid 1000 --gid finance --shell /bin/bash --create-home finance

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown -R finance:finance /app

USER finance

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/finance/.local/bin:${PATH}"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "60", \
     "--access-logfile", "-", "--error-logfile", "-"]
