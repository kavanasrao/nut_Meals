# syntax=docker/dockerfile:1

########################
# Stage 1: build deps  #
########################
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

########################
# Stage 2: runtime     #
########################
FROM python:3.11-slim AS runtime

ARG SERVICE_USER=procurement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/${SERVICE_USER}/.local/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash ${SERVICE_USER}

USER ${SERVICE_USER}
WORKDIR /home/${SERVICE_USER}/app

COPY --from=builder --chown=${SERVICE_USER}:${SERVICE_USER} /root/.local /home/${SERVICE_USER}/.local
COPY --chown=${SERVICE_USER}:${SERVICE_USER} app ./app
COPY --chown=${SERVICE_USER}:${SERVICE_USER} alembic ./alembic
COPY --chown=${SERVICE_USER}:${SERVICE_USER} alembic.ini .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# In production, terminate TLS at the ingress/load balancer (see docs/DEPLOYMENT.md);
# the app itself serves plain HTTP inside the cluster network.
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--timeout", "60"]
