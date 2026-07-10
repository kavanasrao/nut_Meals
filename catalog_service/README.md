# Catalog Service — nut_Meals

Handles product catalog management, SEO metadata, customer reviews, and the
URL redirect manager. One of several independently deployable microservices
in the nut_Meals backend.

## Stack
FastAPI (async) · SQLAlchemy 2.0 (async) + Alembic · PostgreSQL · Redis · Celery · Docker · GitHub Actions

## Local development

```bash
cp .env.example .env
docker compose up --build
```

This starts Postgres, Redis, the API (`:8000`, auto-reload), a Celery worker,
Celery beat, and runs migrations automatically via the `migrate` service.

API docs: http://localhost:8000/docs

## Running tests

```bash
docker compose up -d db-test redis
CATALOG_DATABASE_URL=postgresql+asyncpg://catalog:catalog@localhost:5433/catalog_test_db \
  pytest
```

Coverage is enforced at **≥80%** (`pytest.ini` / `pyproject.toml`) and reported
in CI as a PR comment.

## Database migrations

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Architecture

```
app/
  models/      SQLAlchemy ORM models (Product, Category, Review, Redirect, ...)
  schemas/     Pydantic request/response schemas
  services/    Business logic, DB access, inventory integration
  routers/     FastAPI route handlers (thin — delegate to services)
  tasks/       Celery tasks (moderation side-effects, redirect analytics)
  core/        RBAC, audit logging, security middleware, logging config
alembic/       Migrations
tests/         Pytest unit + integration tests
```

## Security

- **HTTPS enforced** in non-local environments (`HTTPSEnforcementMiddleware`), with HSTS and standard hardening headers.
- **RBAC**: JWT bearer tokens carry a `role` claim (`viewer`, `customer`, `catalog_admin`, `moderator`, `superadmin`); endpoints declare required roles via `require_roles(...)`.
- **Audit logs**: every admin mutation (product/category/review-moderation/redirect changes) writes an `AuditLog` row with actor, action, resource, and IP.
- **Secrets**: none are hardcoded. `JWT signing key`, DB credentials, and other secrets are injected as environment variables by the deploy pipeline, which pulls them from **OCI Vault** (see `CATALOG_OCI_VAULT_OCID` / the `deploy` job in the CI workflow). `.env` is for local dev only and is git-ignored.

## Background jobs (Celery)

| Task | Trigger | Purpose |
|---|---|---|
| `recompute_rating_aggregate_task` | Review moderation decision | Recompute average rating / review count |
| `sync_redirect_analytics_task` | Every redirect resolution | Analytics pipeline hook |
| `flush_redirect_analytics` | Hourly (beat) | Aggregate hit-count reporting |
| `cleanup_old_redirect_logs` | Daily (beat) | Purge redirect logs older than 180 days |

## CI/CD

`.github/workflows/catalog-ci-cd.yml`:
1. **test** — ruff lint, Alembic migration against a real Postgres service container, pytest with coverage gate (≥80%).
2. **build-and-push** — multi-arch (amd64/arm64) Docker build via buildx + QEMU, pushed to GHCR, for both the API and worker images.
3. **deploy** — pulls runtime secrets from OCI Vault and rolls out the new image (kubectl/helm step — placeholder, wire up to your cluster).

## Inventory integration

Stock availability is not owned by Catalog. `app/services/inventory_client.py`
calls the Inventory microservice (`CATALOG_INVENTORY_SERVICE_URL`) for live
stock per SKU, and falls back to the last cached `is_in_stock_cache` flag on
`ProductVariant` if Inventory is unreachable.
