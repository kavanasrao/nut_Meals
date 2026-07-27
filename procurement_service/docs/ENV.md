# Environment Variables

Loaded via `pydantic-settings` (`app/config.py`) from real environment
variables first, falling back to a local `.env` file (see `.env.example`).
**Never commit a populated `.env`.** In staging/production, values marked
🔒 are injected by the deployment pipeline after being pulled from **OCI
Vault** — see `DEPLOYMENT.md`.

| Variable | Default | Description |
|---|---|---|
| `SERVICE_NAME` | `procurement-service` | Used in logs and `/health` |
| `ENV` | `development` | `development` \| `staging` \| `production`; tightens CORS in `production` |
| `DEBUG` | `false` | Enables SQL echo + verbose logging |
| `API_V1_PREFIX` | `/api/v1` | Mount path for all routers |
| `DATABASE_URL` 🔒 | `postgresql+asyncpg://...localhost:5432/procurement_db` | Async SQLAlchemy DSN |
| `DATABASE_POOL_SIZE` | `10` | SQLAlchemy pool size |
| `DATABASE_MAX_OVERFLOW` | `20` | SQLAlchemy overflow connections |
| `REDIS_URL` | `redis://localhost:6379/0` | General Redis (cache, future use) |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Celery result store |
| `JWT_SECRET_KEY` 🔒 | — | Shared secret with the Auth service for verifying bearer tokens |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_AUDIENCE` | `nut-meals` | Expected `aud` claim |
| `FINANCE_SERVICE_BASE_URL` | `http://finance-service:8000` | Base URL for the Finance Service client |
| `FINANCE_SERVICE_API_KEY` 🔒 | — | Bearer key sent to the Finance Service |
| `OCI_VAULT_ID` | — | Consumed only by the deploy pipeline/bootstrap script, not the app process |
| `OCI_VAULT_COMPARTMENT_ID` | — | Same as above |
| `PO_REMINDER_DAYS_BEFORE_DUE` | `2` | Delivery-reminder lead time (days) |
| `INVOICE_RECONCILIATION_INTERVAL_MINUTES` | `30` | Periodic 3-way-match sweep interval |

## Local development

```bash
cp .env.example .env
# edit values as needed — defaults work with docker-compose.yml out of the box
```

## CI

The GitHub Actions workflow (`.github/workflows/procurement-ci.yml`) sets
`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, and `FINANCE_SERVICE_API_KEY`
directly as job-level `env:` values pointing at the ephemeral `postgres`/
`redis` service containers — no Vault access is needed for tests.
