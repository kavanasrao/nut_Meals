# nut_meals Security Service

Governance, monitoring, and compliance service for the nut_meals microservices
platform. Provides:

- **WAF** — DB-configurable rules (SQLi, XSS, CSRF, IP blocklist, rate limiting),
  enforced via an ASGI middleware and available to other services through
  `POST /waf/evaluate`.
- **Audit Logs** — centralized, append-only log of critical actions across
  services (orders, payments, inventory, RBAC changes, WAF changes, etc.),
  ingested synchronously (`POST /audit/logs`) or via a Redis/Celery pipeline
  for high-volume producers, with async CSV/JSON export.
- **Compliance Dashboards** — versioned report definitions (PCI DSS, GDPR,
  SOC2) that run a set of checks against audit logs, RBAC bindings, and WAF
  incidents, producing a readiness score + findings for the Admin CMS.
- **RBAC** — fine-grained roles/permissions (`admin`, `finance`, `logistics`,
  `support`, plus custom roles), with a `POST /rbac/check` endpoint other
  services call at authorization time.

## Architecture

```
app/
  main.py            FastAPI app, middleware wiring, health/ready probes
  config.py          Settings (env-driven; secrets from OCI Vault in prod)
  database.py         Async SQLAlchemy engine/session
  models/            ORM models (waf, audit, compliance, rbac)
  schemas/           Pydantic request/response schemas
  api/
    deps.py           JWT auth + permission-enforcement dependency
    routes/           waf.py, audit.py, compliance.py, rbac.py
  services/          Business logic (WafEngine, AuditService, ComplianceService, RbacService)
  middleware/         WafMiddleware, SecurityHeadersMiddleware
  tasks/              Celery app + audit ingestion/export/cleanup tasks
alembic/              Migrations (0001_initial creates all tables)
tests/                pytest suite (unit + integration, ≥80% coverage gate)
```

## Local development

```bash
cp .env.example .env
make dev          # starts security-service, celery worker/beat, postgres, redis
```

The service listens on `localhost:8010` (mapped from container port 8000).
Alembic migrations run automatically on container start.

To integrate into the platform-wide `docker-compose.yml`, merge the services
in this repo's `docker-compose.yml` into the root compose file so all
services share the `nutmeals-net` network (already declared here to match
that convention).

## Running tests

Tests require a real Postgres instance (models use native `UUID`/`JSONB`/`ENUM`
types) and Redis (for WAF rule caching and rate limiting):

```bash
make test          # spins up docker-compose.test.yml, migrates, runs pytest, tears down
```

Coverage is enforced at 80% via `pytest.ini` (`--cov-fail-under=80`); CI fails
the build below that threshold.

## Authorization model

Every route (other than the intentionally-open `/waf/evaluate` and `/rbac/check`
service-to-service endpoints) is gated by `require_permission("<code>")` in
`app/api/deps.py`, which re-checks the live RBAC tables on each request rather
than trusting only JWT role claims — so a revoked role takes effect immediately.

Permission codes follow `<service>:<action>`, e.g. `waf:manage_rules`,
`audit:export`, `compliance:manage`, `rbac:manage`. Seed roles/permissions via
the `/rbac/permissions`, `/rbac/roles`, and `/rbac/bindings` endpoints (an
Alembic data-migration or a `scripts/seed_rbac.py` would typically do this
once at bootstrap — not included here since exact role/permission sets are
an operational decision for the platform team).

## CI/CD

`.github/workflows/security-service-ci.yml`:
1. **lint** — ruff + black
2. **test** — pytest against Postgres+Redis service containers, coverage gate
3. **build-and-push** — multi-arch (amd64/arm64) image via Buildx+QEMU, pushed
   to GHCR on `main`
4. **deploy** — placeholder step; wire to your actual deploy mechanism (OKE
   rollout, ArgoCD, Helm/Terraform apply)

## Secrets

`SECURITY_JWT_SECRET`, `DATABASE_URL` credentials, and other secrets are
injected via OCI Vault at container start in staging/production — never
committed. `.env` is for local dev only and is gitignored.
