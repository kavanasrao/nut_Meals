# Admin CMS Service

Dashboards, content management, and analytics for nut_Meals administrators.
Runs as an independent microservice (own DB, migrations, Dockerfile, CI/CD
pipeline), extending — but separate from — `admin-service`.

## Features

| Feature | Endpoints | Notes |
|---|---|---|
| Finance Dashboards | `/api/v1/finance/*` | Cached rollups from the Finance service; async CSV/PDF/XLSX report export via Celery |
| Returns Management | `/api/v1/returns/*` | Approve/reject returns, tiers A–C, integrates with Orders + Logistics |
| Content/Blog Manager | `/api/v1/content/*` | Blog posts, announcements, FAQs; SEO metadata; scheduled publishing |
| Analytics | `/api/v1/analytics/*` | KPI snapshots (conversion, churn, repeat customers, GMV/AOV) from Orders/Payments/Inventory |

## Local development

```bash
cp .env.example .env
docker compose up -d db redis
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Run the full stack (API + worker + beat) via Docker Compose:

```bash
docker compose up --build
```

## Running tests

Tests require a real Postgres instance (native `UUID`/`JSONB`/`ARRAY`/`INET`
column types aren't supported by SQLite):

```bash
docker compose --profile test up -d db-test
pytest
```

Coverage report is written to `coverage.xml`; the suite fails if coverage
drops below 80% (`--cov-fail-under=80` in `pytest.ini`).

## Background jobs (Celery)

| Task | Schedule | Purpose |
|---|---|---|
| `aggregate_daily_kpis_task` | 01:00 UTC daily | Compute yesterday's KPI snapshot |
| `refresh_current_month_summary_task` | hourly | Refresh finance summary cache |
| `publish_due_scheduled_content_task` | every minute | Publish scheduled blog posts/announcements |
| `generate_finance_report_task` | on-demand (enqueued by API) | Render + upload exportable finance reports |

Run locally:

```bash
celery -A app.tasks.celery_app worker --loglevel=info
celery -A app.tasks.celery_app beat --loglevel=info
```

## Security

- **RBAC**: every admin endpoint requires a verified JWT (issued by
  `admin-service`) plus one of the roles defined in `AdminRole`
  (`app/core/security.py`).
- **Audit logs**: all state-changing actions (approve/reject returns,
  publish/delete content, request finance reports) write an
  `AuditLogEntry` row (`app/core/audit.py`).
- **Secrets**: DB credentials, JWT keys, and the internal service token
  are injected at runtime from OCI Vault — never committed to source
  control. `.env.example` contains dev-only placeholders.
- **HTTPS**: enforced via `HTTPSRedirectMiddleware` in production
  (`ADMIN_CMS_FORCE_HTTPS=true`); TLS termination happens at the
  ingress/load balancer in the cluster.

## CI/CD

See `.github/workflows/admin-cms-ci.yml`:

1. **lint** — ruff + black
2. **test** — pytest against ephemeral Postgres + Redis service containers, coverage gate at 80%
3. **build-and-push** — multi-arch (amd64/arm64) Docker images for API and worker, pushed to GHCR
4. **deploy** — staging deployment (main branch only)

## Database migrations

```bash
alembic revision --autogenerate -m "add new_field to content_items"
alembic upgrade head
```
