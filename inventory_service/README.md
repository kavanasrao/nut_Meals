# nut_Meals — Inventory Service

Independent FastAPI microservice handling warehouses, stock, Bill of
Materials (BOM), batch production, and order-time stock reservations for
the nut_Meals backend.

## Architecture

- **FastAPI** (async) — HTTP API, `app/main.py`
- **PostgreSQL** via SQLAlchemy 2.0 async ORM — `app/models/`
- **Alembic** — schema migrations, `alembic/`
- **Redis + Celery** — background jobs (reservation TTL release, batch
  completion notifications), `app/tasks/`
- **RBAC** — role-scoped JWT bearer auth, `app/core/security.py`
- Runs as its own container with its own DB, independent of other
  nut_Meals services (Orders, Catalog, etc.), communicating over HTTP.

## Domain model

| Concept | Table(s) | Notes |
|---|---|---|
| Warehouse | `warehouses` | Location + capacity |
| Item (SKU) | `items` | Raw ingredient, component, or finished product |
| Stock | `stock_levels` | Per warehouse/item; splits on-hand vs reserved |
| Transfer | `stock_transfers` | Warehouse-to-warehouse moves |
| BOM | `bill_of_materials`, `bom_components` | Versioned recipes |
| Batch | `production_batches` | planned → in_progress → completed/failed/cancelled |
| Reservation | `stock_reservations` | active → confirmed / released / expired |
| Audit log | `stock_movement_logs` | Immutable, append-only, drives lot traceability + CSV export |

## Local development

```bash
cp .env.example .env
docker compose up --build
docker compose run --rm inventory-migrate   # first time / after new migrations
```

API: http://localhost:8001/docs
Postgres: localhost:5433 · Redis: localhost:6380

## Running tests

```bash
pip install -r requirements-dev.txt
pytest                      # uses an in-memory SQLite engine, no services needed
```

CI additionally runs the suite against a real Postgres service container
(see `.github/workflows/inventory-ci.yml`) to catch any Postgres-specific
behavior (enum types, `SELECT ... FOR UPDATE`, etc.) that SQLite can't
fully emulate.

Coverage gate: **80%** (`--cov-fail-under=80`), enforced in CI.

## Creating a migration

```bash
alembic revision -m "add new_column to items" --autogenerate
```

Autogenerate output should always be reviewed by hand before committing —
it can miss server-side defaults, enum changes, and renames.

## Reservation flow (Orders integration)

1. `POST /api/v1/reservations` — Orders service holds stock at checkout.
   A Celery task is scheduled to auto-release the hold at `expires_at`.
2. `POST /api/v1/reservations/{id}/confirm` — called on payment success;
   permanently deducts stock.
3. `POST /api/v1/reservations/{id}/release` — called on payment failure;
   also happens automatically via Celery if nothing calls confirm/release
   before the reservation's TTL (`RESERVATION_TTL_SECONDS`, default 15 min).
   A Celery beat sweep runs every 2 minutes as a safety net.

## RBAC roles

| Role | Can do |
|---|---|
| `inventory:admin` | Everything |
| `inventory:manager` | Manage warehouses, items, BOMs, batches |
| `inventory:operator` | Execute transfers, stock adjustments, start batches |
| `inventory:orders_service` | Create/confirm/release reservations only (service-to-service token) |
| `inventory:viewer` | Read-only access, including compliance reports |

## Secrets management

No secrets are stored in this repository. `DATABASE_URL`, `JWT_SECRET_KEY`,
`REDIS_URL`, and registry credentials are fetched from **OCI Vault** by the
CI/CD deploy job (`.github/workflows/inventory-ci.yml`, `deploy` job) and
injected as environment variables at deploy time. Locally, `.env` holds
non-secret dev-only placeholder values.

## Compliance & traceability

Every stock-affecting action (adjustment, transfer, production consume/
yield, reservation hold/release/confirm) writes an immutable row to
`stock_movement_logs` including actor, lot number, and a reference id
(order/batch/transfer id). Query via `GET /api/v1/reports/movements` or
export as CSV via `GET /api/v1/reports/movements/export.csv`.

## Docker build targets

The single `Dockerfile` defines three targets sharing one base image:

- `runtime` — the FastAPI API process
- `worker` — `celery worker`
- `beat` — `celery beat` (reservation-expiry sweep scheduler)

Multi-arch (amd64/arm64) images are built via `docker buildx` in CI using
QEMU + Buildx, and pushed to GHCR on `main`/`develop`.
