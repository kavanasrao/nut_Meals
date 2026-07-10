# nut_Meals Finance Service

Double-entry ledger accounting, trial balance / P&L reporting, and payment
gateway settlement reconciliation, run as an independent FastAPI
microservice within nut_Meals' backend.

## Architecture

```
app/
  core/        config, DB session, JWT auth/RBAC, audit log helper
  models/      SQLAlchemy ORM models (ledger, journal, reconciliation, audit)
  schemas/     Pydantic request/response models
  services/    business logic (ledger, journal, trial balance, P&L, reconciliation)
  routers/     FastAPI route handlers
  tasks/       Celery app + background jobs (reconciliation, report snapshots)
  main.py      FastAPI app entrypoint
alembic/       DB migrations
tests/         pytest unit + integration tests (80%+ coverage required)
```

Each domain service in the nut_Meals platform (Orders, Payments, Finance,
...) owns its own database and its own deployable container. The Finance
service never joins directly against another service's database; it calls
the Orders service's internal HTTP API to reconcile settlements
(`app/services/order_client.py`).

## Core concepts

- **Double-entry ledger**: every financial fact is a balanced set of debit/
  credit `JournalLine`s under a `JournalEntry`. Amounts are stored as
  `BigInteger` minor units (paise) to avoid floating-point rounding errors.
  Posted entries are immutable; corrections are made via reversing entries.
- **Trial balance**: `GET /api/v1/reports/trial-balance?as_of_date=...`
- **P&L**: `GET /api/v1/reports/pnl?year=2026&granularity=monthly&period_index=7`
  or `GET /api/v1/reports/pnl/custom?period_start=...&period_end=...`
- **Reconciliation**: `POST /api/v1/reconciliation/runs` ingests a settlement
  batch and triggers async Celery matching against the Orders service;
  mismatches/unmatched settlements become `ReconciliationException` rows
  visible at `GET /api/v1/reconciliation/exceptions`.
- **Audit log**: every mutation writes an append-only `AuditLog` row in the
  same DB transaction (see `app/core/audit.py`). Read via
  `GET /api/v1/audit-logs` (admin only).

## Local development

```bash
cp .env.example .env
docker network create nutmeals-shared-net  # once, shared across services
docker compose up --build
# API:    http://localhost:8000/docs
# Postgres: localhost:5433, Redis: localhost:6380
```

## Running tests

Tests require a real PostgreSQL instance (models use Postgres-specific
UUID/JSONB/ENUM types and CHECK constraints):

```bash
pip install -r requirements-dev.txt
export FINANCE_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/finance_test_db
export FINANCE_JWT_SECRET_KEY=test-secret-key
alembic upgrade head
pytest   # enforces >=80% coverage, see pytest.ini
```

## Migrations

```bash
alembic revision -m "add new_column to ledger_accounts"  # create a new migration
alembic upgrade head                                      # apply
alembic downgrade -1                                       # roll back one
```

## Security

- JWT bearer auth validated against the platform Auth service's signing key
  (`app/core/security.py`); role claims (`finance:viewer`, `finance:accountant`,
  `finance:reconciler`, `finance:admin`) gate individual endpoints.
- HTTPS is enforced via the `enforce_https` dependency (checks
  `X-Forwarded-Proto`, since TLS terminates at the load balancer).
- Secrets (DB credentials, JWT key, gateway API keys) are never committed;
  they're injected as environment variables by the deploy pipeline, which
  reads them from **OCI Vault** at deploy time.
- All mutating actions are audit-logged; audit rows are insert-only.

## CI/CD

`.github/workflows/finance-ci-cd.yml` runs on every push/PR touching this
service: lint (ruff) → test (pytest against a Postgres service container,
80% coverage gate) → multi-arch Docker build (amd64 + arm64, via buildx +
QEMU) pushed to GHCR → deploy (rolling update, migrations run pre-deploy).
