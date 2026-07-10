# syntax=docker/dockerfile:1.7
# Multi-arch build (linux/amd64, linux/arm64) via `docker buildx build --platform linux/amd64,linux/arm64`

FROM --platform=$BUILDPLATFORM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Runtime stage ----
FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r logistics && useradd -r -g logistics -d /app logistics

WORKDIR /app

COPY --from=builder /root/.local /home/logistics/.local
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

ENV PATH=/home/logistics/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN chown -R logistics:logistics /app /home/logistics/.local
USER logistics

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
