# nut_meals — Logistics Service

Carrier integrations, serviceability + rules-engine carrier selection,
shipment tracking, reverse logistics (returns), and compliance audit
reporting for the nut_meals platform. Runs as an independent FastAPI
microservice with its own Postgres schema, Celery workers, and CI/CD pipeline.

## Architecture

```
app/
  main.py            FastAPI app + route registration
  config.py          Settings (env-driven; secrets from OCI Vault at deploy)
  database.py         Async SQLAlchemy engine/session
  models/             ORM models (carriers, shipments, tracking_events, audit_logs)
  schemas/             Pydantic request/response models
  adapters/            Carrier adapter pattern (base + Delhivery + India Post + registry)
  services/            Business logic: serviceability, allocation/fallback, tracking, returns, audit, notification
  api/routes/          FastAPI routers (carriers, tracking/shipments, returns, reports)
  core/                Security (JWT/RBAC), Redis client, Celery app
  tasks/               Celery tasks: tracking sync, serviceability cache refresh
alembic/               DB migrations
tests/unit/            Unit tests (mocked adapters/redis)
tests/integration/     End-to-end API tests (httpx ASGITransport)
```

## Carrier adapter pattern

Every carrier implements `BaseCarrierAdapter` (`check_serviceability`,
`create_shipment`, `create_reverse_pickup`, `fetch_tracking`), normalizing
provider-specific responses into shared dataclasses. `app/adapters/registry.py`
maps `CarrierCode` -> adapter instance. Adding a carrier = one adapter class +
one registry line + a `carriers` row.

## Serviceability, rules engine & fallback

- `services/serviceability.py`: checks all active carriers in parallel,
  caches results in Redis (`serviceability_cache_ttl`, default 1h), and scores
  each serviceable option on a weighted blend of cost, speed, and reliability
  (`weight_cost`/`weight_speed`/`weight_reliability` in `Settings`).
- `services/allocation.py`: books the top-ranked carrier; if booking fails,
  automatically retries with the next-ranked carrier, logging a
  `carrier_fallback` audit event for each failed attempt.

## Tracking

- `GET /v1/shipments/{id}/tracking?force_refresh=true` pulls live checkpoints.
- `app/tasks/tracking_sync.py` runs every 15 minutes via Celery beat, fanning
  out one task per active shipment so a single slow/failing carrier call
  doesn't block the batch. Status changes sync to Orders and trigger customer
  notifications (email/SMS/WhatsApp) via the Messaging service.

## Returns / reverse logistics

`POST /v1/returns` books a reverse pickup against the original carrier;
`services/returns.complete_return_and_restock` notifies Inventory once the
return is received back at the warehouse.

## Security & compliance

- JWT auth (RS256, shared public key) + role-based access control
  (`require_roles(...)` dependency) on every route.
- HTTPS enforced via `HTTPSRedirectMiddleware` + `X-Forwarded-Proto` check.
- Every state-changing action writes an `AuditLog` row; `GET
  /v1/reports/audit-log.csv` exports a compliance report for a date range.
- All carrier tokens, DB credentials, and JWT keys are injected as env vars
  from OCI Vault at deploy time — never committed to source.

## Running locally

```bash
cp .env.example .env
docker network create nut_meals_net   # if not already created by the root compose
docker compose up --build
alembic upgrade head
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

## CI/CD

`.github/workflows/logistics-ci-cd.yml`: lint (ruff/mypy) → test + coverage
(fails under 80%) → multi-arch (amd64/arm64) Docker build & push to GHCR for
both the API and worker images → deploy stage (wire to your k8s/ArgoCD/OCI
target).
