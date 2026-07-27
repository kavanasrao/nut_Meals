# Procurement Service — nut_meals

Microservice responsible for vendor management, purchase orders, goods
receipt notes (GRN), and purchase invoices, with a ledger integration to
the Finance Service.

## Stack

| Concern        | Technology                          |
|-----------------|--------------------------------------|
| API framework   | FastAPI (async), Python 3.11        |
| ORM             | SQLAlchemy 2.0 (async) + asyncpg    |
| Migrations      | Alembic                              |
| Database        | PostgreSQL 16                        |
| Background jobs | Celery + Redis (broker/backend)      |
| Auth            | JWT (HS256), shared secret via Vault |
| Tests           | pytest, pytest-asyncio, pytest-cov   |
| CI/CD           | GitHub Actions                       |
| Container       | Docker (multi-stage, non-root)       |

## Repository layout

```
procurement_service/
├── app/
│   ├── main.py              # FastAPI app, routers, health checks
│   ├── config.py            # env-driven settings
│   ├── database.py          # async engine/session
│   ├── core/                # security (JWT) + RBAC
│   ├── models/               # SQLAlchemy models
│   ├── schemas/              # Pydantic request/response models
│   ├── services/             # business logic
│   ├── routers/               # FastAPI route handlers
│   └── tasks/                # Celery app + background tasks
├── alembic/                  # DB migrations
├── tests/
│   ├── unit/                 # service-layer + task logic tests
│   └── integration/          # full HTTP-API tests
├── docs/                      # this documentation set
├── Dockerfile                 # API image
├── Dockerfile.worker           # Celery worker/beat image
├── docker-compose.yml
└── .github/workflows/procurement-ci.yml
```

## Quick start (local development)

```bash
cp .env.example .env          # fill in local secrets
docker compose up --build     # starts db, redis, api, worker, beat
```

The API is then available at `http://localhost:8010/api/v1/docs` (Swagger UI).

Run migrations manually if needed:

```bash
docker compose run --rm procurement-migrate
```

## Running tests

Requires a local Postgres reachable at `DATABASE_URL` (the `docker-compose.yml`
`procurement-db` service works fine for this):

```bash
pip install -r requirements-dev.txt
alembic upgrade head
pytest
```

Coverage is enforced at **≥80%** (`pytest.ini` sets `--cov-fail-under=80`);
CI fails the build below that threshold.

## Further documentation

- [`docs/API.md`](docs/API.md) — endpoint reference and RBAC matrix
- [`docs/SCHEMA.md`](docs/SCHEMA.md) — database schema and entity relationships
- [`docs/ENV.md`](docs/ENV.md) — environment variable reference
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — deployment guide, secrets, TLS
