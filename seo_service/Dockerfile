# syntax=docker/dockerfile:1
# Multi-stage Dockerfile for nut_Meals SEO Service.
# Built for both linux/amd64 and linux/arm64 via `docker buildx build --platform`.

FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim AS runtime

# Non-root user for defense in depth.
RUN groupadd -r seo && useradd -r -g seo -d /home/seo -m seo

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /home/seo/.local
COPY --chown=seo:seo . .

ENV PATH=/home/seo/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN mkdir -p /data/ai-exports && chown -R seo:seo /data

USER seo

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Runs migrations then starts the API. Celery worker/beat use separate
# commands (see docker-compose.yml) against this same image.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"]
