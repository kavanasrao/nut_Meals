# Deployment Guide

## Images

Two images are built from this service:

- `Dockerfile` → API image, runs `gunicorn` with `uvicorn.workers.UvicornWorker` (4 workers), exposes `8000`, has a `/health` HTTP healthcheck.
- `Dockerfile.worker` → Celery worker/beat image, same dependency layer, different entrypoint (`celery -A app.tasks.celery_app.celery_app worker|beat`).

Both are multi-stage (builder + slim runtime), run as a non-root user, and
install only what's declared in `requirements.txt`.

## Local stack

```bash
cp .env.example .env
docker compose up --build
```

This brings up: `procurement-db` (Postgres), `procurement-redis`,
`procurement-migrate` (runs `alembic upgrade head` then exits),
`procurement-api` (port `8010:8000`), `procurement-worker`, and
`procurement-beat`. `docker-compose.yml` is written to be included/merged
into the umbrella nut_meals compose file that runs all microservices on a
shared network.

## CI/CD (GitHub Actions)

`.github/workflows/procurement-ci.yml` runs on push/PR to `main`/`develop`
touching this service's path:

1. **lint** — `ruff check` + `mypy`
2. **test** — spins up ephemeral Postgres + Redis service containers, runs
   `alembic upgrade head`, then `pytest` with `--cov-fail-under=80`
   (build fails if coverage drops below 80%)
3. **security-scan** — `pip-audit` against `requirements.txt`
4. **build-and-push** — builds and pushes both images to `ghcr.io`, tagged
   `<branch>-<short-sha>` and `latest`, only on `push` to `main`/`develop`
5. **deploy-staging** / **deploy-production** — gated on `develop`/`main`
   respectively; `production` uses a GitHub Environment with a manual
   approval gate

## Secrets & OCI Vault

No secret is ever committed or hardcoded. In deployed environments:

1. The deployment pipeline (or an init container / sidecar, depending on
   the target platform) authenticates to **OCI Vault** using workload
   identity and fetches: `DATABASE_URL` (or its component parts),
   `JWT_SECRET_KEY`, `FINANCE_SERVICE_API_KEY`.
2. These are injected as environment variables into the running
   container — the application only ever reads them via
   `app/config.py::Settings`, which has no knowledge of Vault itself.
3. `OCI_VAULT_ID` / `OCI_VAULT_COMPARTMENT_ID` are used by the
   bootstrap/deploy tooling to locate the correct vault and compartment;
   they are not read by the FastAPI process.
4. Rotate secrets by updating the Vault secret version and rolling the
   deployment (no code change required).

## HTTPS / TLS

The container serves plain HTTP on `8000` inside the cluster network. TLS
is terminated at the ingress/load balancer in front of the service, per
platform convention (e.g. an OCI Load Balancer or Kubernetes Ingress with
a managed certificate). Do not add TLS termination inside the app.

## Database migrations in production

Migrations run as a **separate step** (`procurement-migrate` in compose;
an equivalent one-shot Job in Kubernetes) before the new API/worker
revision is rolled out, so the schema is always ready before new code
tries to use it:

```bash
alembic upgrade head
```

Roll forward only — write migrations to be backward-compatible with the
previous app version during a rolling deploy (expand/contract pattern for
breaking column changes).

## Health checks

- `GET /health` — liveness (process is up)
- `GET /health/ready` — readiness (executes `SELECT 1` against Postgres)

Wire `/health` to the container's liveness probe and `/health/ready` to
its readiness probe.

## Scaling

- API: stateless, scale horizontally behind the load balancer; `gunicorn`
  worker count (`--workers 4`) is per-pod and should be tuned to CPU
  request/limit.
- Celery worker: scale by adding replicas; `worker_prefetch_multiplier=4`
  and `task_acks_late=True` are already set for safer retry semantics.
- Celery beat: run exactly **one** replica (it's the scheduler, not a
  worker) — use a leader-election sidecar or a single dedicated
  deployment if your platform doesn't guarantee singleton pods natively.
