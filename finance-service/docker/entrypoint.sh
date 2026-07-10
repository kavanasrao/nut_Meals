#!/bin/bash
# Entrypoint for the Finance service container.
# Runs pending Alembic migrations (idempotent) before starting the process
# given as CMD (gunicorn for the API, or `celery worker`/`celery beat` when
# this same image is reused for background workers - see docker-compose.yml).
set -euo pipefail

if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
    echo "[entrypoint] Running Alembic migrations..."
    alembic upgrade head
fi

echo "[entrypoint] Starting: $*"
exec "$@"
