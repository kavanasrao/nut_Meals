# Cart/Checkout Extensions Service

Independently deployed microservice extending nut_Meals' core Cart/Checkout
service with:

- **Gift Orders** — mark an order as a gift, attach recipient details, gift
  message, and gift-wrap/delivery-date options.
- **Subscriptions** — weekly/monthly recurring meal plans with full
  lifecycle management (create, pause, resume, cancel) and automated
  renewal billing via the Payments service.
- **One-Click Login Checkout** — short-lived, single-use tokens plus saved
  address/payment-method lookup for fast repeat checkout.

## Stack

FastAPI (async) · PostgreSQL + SQLAlchemy 2.0 (async) · Alembic · Celery +
Redis · Docker (multi-arch) · GitHub Actions.

## Local development

```bash
cp .env.example .env
docker compose up -d postgres redis
docker compose run --rm migrate
docker compose up api celery-worker celery-beat
```

API is served at `http://localhost:8000`; interactive docs at `/docs`.

## Running tests

Tests run against a real Postgres instance (models use Postgres-specific
UUID/JSONB columns).

```bash
docker compose up -d postgres
pip install -r requirements-dev.txt
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/cart_checkout_ext_test pytest
```

Coverage report is written to `coverage.xml`; CI fails the build under 80%.

## Database migrations

```bash
alembic revision --autogenerate -m "add new_column"
alembic upgrade head
```

## Background jobs

- `process_due_renewals` (hourly): charges due subscriptions via the
  Payments service, advances `next_renewal_date`, marks `past_due` after
  3 consecutive failures.
- `send_upcoming_renewal_notices` (hourly, offset): queues renewal
  reminders `RENEWAL_NOTICE_DAYS` before the next charge.
- `send_gift_notification`: notifies a gift recipient once, retried up to
  3 times on transient failure.

## Security

- All endpoints require a JWT issued by the upstream auth service
  (`Authorization: Bearer <token>`), validated with a shared signing
  secret sourced from OCI Vault at deploy time (never committed).
- RBAC via `RequireRole` dependencies — customers can only act on their
  own resources; an `admin` role can act on behalf of support workflows.
- Structured JSON audit logs for every gift/subscription/one-click
  mutation, shipped to the platform's centralized log pipeline.
- Payment data is never stored directly — only opaque processor tokens
  from the Payments service, keeping this service out of PCI scope.
- HTTPS enforced at the ingress; a defense-in-depth middleware check
  rejects non-HTTPS traffic in production.

## Service boundaries

This service does not own customer identity, raw payment data, or the
base order record — those remain in the core Cart/Checkout, Payments, and
Customer Profile services respectively. Cross-service references (e.g.
`order_id`, `payment_method_token`) are stored as opaque identifiers.
