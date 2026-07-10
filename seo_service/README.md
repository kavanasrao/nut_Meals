# nut_Meals SEO Service

Independent FastAPI microservice handling dynamic sitemaps, schema.org
structured data, AI-crawler discovery readiness, and redirect/canonical
URL management for nut_Meals.

## Layout

```
app/
  main.py                 FastAPI app, middleware, routers
  config.py               Settings (env-driven, Vault-backed secrets in prod)
  database.py             Async SQLAlchemy engine/session
  models/                 ORM models (sitemap, structured_data, redirects, ai_discovery)
  schemas/                Pydantic request/response schemas
  api/                    Route modules per feature area
  services/               Business logic + Catalog/Reviews/Blog HTTP client
  tasks/                  Celery app + background jobs
  core/                   RBAC/JWT security, audit logging
alembic/                  DB migrations
tests/                    pytest suite (>=80% coverage gate)
Dockerfile                Multi-stage, non-root, multi-arch build
docker-compose.yml        Local dev stack (Postgres, Redis, API, worker, beat)
.github/workflows/        CI/CD: lint, test, multi-arch build+push, deploy
```

## Local development

```bash
cp .env.example .env
docker network create nut_meals_net   # if not already created by other services
docker compose up --build
```

- API: http://localhost:8004/healthz
- Sitemap index: http://localhost:8004/sitemaps/sitemap-index.xml
- AI robots directives: http://localhost:8004/ai-discovery/robots-ai.txt

Run migrations manually if needed:
```bash
docker compose exec seo-api alembic upgrade head
```

## Running tests

```bash
pip install -r requirements.txt
pytest
```

Tests run against in-memory SQLite for speed/isolation and mock upstream
HTTP calls (`respx`) — no external services required.

## Key endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/sitemaps/sitemap-index.xml` | public | Root sitemap index |
| GET | `/sitemaps/{file}.xml` | public | Individual paginated sitemap |
| POST | `/sitemaps/rebuild` | seo_editor/admin | Queue sitemap resync |
| GET | `/structured-data/products/{id}` | public | Cached Product JSON-LD |
| GET | `/structured-data/blog-posts/{id}` | public | Cached BlogPosting JSON-LD |
| POST | `/structured-data/sync` | seo_editor/admin | Resync JSON-LD for one entity |
| GET | `/ai-discovery/products/{id}/metadata` | public | Embedding-ready product metadata |
| POST | `/ai-discovery/export` | seo_editor/admin | Queue bulk NDJSON catalog export |
| GET | `/ai-discovery/export/{batch_id}` | public | Export batch status |
| GET | `/redirects/lookup` | public | Resolve a redirect by source path |
| POST | `/redirects` | seo_editor/admin | Create a redirect rule (audit-logged) |
| PUT | `/redirects/canonical` | seo_editor/admin | Set canonical URL (audit-logged) |

## Security notes

- All mutating endpoints require a valid RS256 JWT (`Authorization: Bearer`)
  and enforce role-based access (`viewer` / `seo_editor` / `admin`).
- HTTPS is enforced at the ingress and re-checked in-app in production.
- Every mutating action against redirects/canonicals writes an immutable
  row to `audit_log_entries` (actor, action, before/after state, IP).
- Runtime secrets (DB URL, JWT public key, AI export signing secret) are
  never committed; they're injected from OCI Vault at container start.
