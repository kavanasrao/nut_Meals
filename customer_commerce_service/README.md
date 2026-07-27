# Customer & Commerce Service

Part of the **Nut Meals** microservices platform. Manages the full shopping experience: cart, wishlist, coupons, addresses, and GST-compliant invoice generation.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Features](#features)
3. [Tech Stack](#tech-stack)
4. [Database Schema](#database-schema)
5. [API Reference](#api-reference)
6. [Environment Variables](#environment-variables)
7. [Local Development](#local-development)
8. [Running Tests](#running-tests)
9. [Deployment Guide](#deployment-guide)
10. [Security](#security)
11. [Background Tasks](#background-tasks)

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│              Customer & Commerce Service              │
│                                                      │
│  FastAPI (async)  ──►  PostgreSQL (asyncpg)          │
│       │                                              │
│       ├──► Redis (session cache / Celery broker)     │
│       │                                              │
│       └──► Celery Workers                            │
│               ├── generate_invoice_pdf               │
│               └── send_abandoned_cart_emails (beat)  │
│                                                      │
│  Internal HTTP calls:                                │
│    ├── Notification Service (abandoned cart emails)  │
│    └── OCI Object Storage  (invoice PDF storage)     │
└──────────────────────────────────────────────────────┘
```

---

## Features

| Domain | Capability |
|--------|-----------|
| **Cart** | CRUD cart items, upsert by product, apply coupon, clear cart |
| **Cart Recovery** | Celery Beat cron every 6 h; notifies Notification Service for carts idle >24 h |
| **Wishlist** | Add / remove products; idempotent add |
| **Coupons** | Percent & fixed discounts, usage limits, per-user limits, expiry, cart-total min |
| **Addresses** | CRUD with default address management; GSTIN for B2B invoices |
| **Invoices** | GST-compliant PDF (CGST + SGST / IGST), Celery async generation, OCI upload |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.115 (Python 3.11) |
| ORM | SQLAlchemy 2 async + asyncpg |
| Migrations | Alembic |
| Cache / Broker | Redis 7 |
| Task queue | Celery 5 + Celery Beat |
| PDF | ReportLab |
| Object Storage | OCI Object Storage |
| Auth | JWT (HS256) — verified against shared secret |
| Tests | pytest-asyncio, httpx AsyncClient, aiosqlite |
| CI/CD | GitHub Actions → GHCR → OKE (OCI Kubernetes) |

---

## Database Schema

```
carts
├── id (UUID PK)
├── user_id (UUID, unique index)
├── is_active (bool)
├── coupon_code (str, nullable)
├── last_activity_at (timestamptz)   ← used by abandoned-cart cron
└── recovery_email_sent_at (timestamptz, nullable)

cart_items
├── id, cart_id → carts.id (CASCADE)
├── product_id, product_name, unit_price
└── quantity, image_url

wishlist_items
├── id, user_id, product_id  (UNIQUE together)
└── product_name, unit_price, image_url

coupons
├── id, code (unique), discount_type (percent|fixed)
├── discount_value, min_order_value, max_discount_cap
├── usage_limit, usage_count, per_user_limit
└── is_active, valid_from, valid_until

coupon_usages
├── id, coupon_id, user_id  (UNIQUE together)
└── order_id, times_used

saved_addresses
├── id, user_id
├── label, full_name, phone
├── line1, line2, city, state, pincode, country
└── is_default, gstin

invoices
├── id, invoice_number (unique), order_id, user_id
├── billing_name, billing_address, billing_gstin
├── subtotal, cgst/sgst/igst rates and amounts
├── discount_amount, total_amount
├── line_items (JSONB snapshot)
└── status (pending|generated|failed|sent), pdf_url, celery_task_id
```

---

## API Reference

Full interactive docs at `/docs` (Swagger) or `/redoc`.

### Cart  `GET|POST|PATCH|DELETE /api/v1/cart`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/cart` | Get current cart |
| POST | `/api/v1/cart/items` | Add item (upserts quantity if same product) |
| PATCH | `/api/v1/cart/items/{item_id}` | Update quantity |
| DELETE | `/api/v1/cart/items/{item_id}` | Remove item |
| DELETE | `/api/v1/cart` | Clear entire cart |
| POST | `/api/v1/cart/coupon` | Apply coupon to cart |

### Wishlist  `/api/v1/wishlist`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/wishlist` | List wishlist items |
| POST | `/api/v1/wishlist` | Add product |
| DELETE | `/api/v1/wishlist/{product_id}` | Remove product |

### Coupons  `/api/v1/coupons`

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/api/v1/coupons` | admin | Create coupon |
| GET | `/api/v1/coupons/{code}` | admin | Get coupon details |
| POST | `/api/v1/coupons/validate` | customer | Validate + compute discount |

### Addresses  `/api/v1/addresses`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/addresses` | List saved addresses |
| POST | `/api/v1/addresses` | Create address |
| PUT | `/api/v1/addresses/{id}` | Update address |
| DELETE | `/api/v1/addresses/{id}` | Delete address |
| PATCH | `/api/v1/addresses/{id}/default` | Set as default |

### Invoices  `/api/v1/invoices`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/invoices` | Create invoice + enqueue PDF |
| GET | `/api/v1/invoices/{id}` | Get invoice + PDF URL |

---

## Environment Variables

See [`.env.example`](.env.example) for the full list with descriptions.

Critical variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | asyncpg connection string |
| `REDIS_URL` | Redis URL for cache |
| `CELERY_BROKER_URL` | Redis URL for Celery tasks |
| `JWT_SECRET_KEY` | Shared JWT signing key (OCI Vault in prod) |
| `OCI_BUCKET_NAME` | Object Storage bucket for invoice PDFs |
| `COMPANY_GSTIN` | Your company's GST number (printed on invoices) |
| `ABANDONED_CART_HOURS` | Inactivity threshold for cart recovery (default 24) |

---

## Local Development

### Prerequisites

- Docker & Docker Compose v2
- Python 3.11+

### Quick Start

```bash
# 1. Clone and navigate
git clone https://github.com/your-org/nut-meals.git
cd nut-meals

# 2. Copy env template
cp customer_commerce_service/.env.example customer_commerce_service/.env
# Edit .env as needed

# 3. Start all services
docker compose up -d db redis

# 4. Run migrations
docker compose run --rm migrate

# 5. Start the API
docker compose up customer-commerce-api

# 6. Visit interactive docs
open http://localhost:8000/docs
```

### Running without Docker

```bash
cd customer_commerce_service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Start API
uvicorn app.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A app.tasks.celery_app.celery_app worker --loglevel=info

# Start Celery Beat scheduler (separate terminal)
celery -A app.tasks.celery_app.celery_app beat --loglevel=info
```

---

## Running Tests

```bash
cd customer_commerce_service

# Install test deps
pip install -r requirements.txt

# Run all tests with coverage
pytest

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v

# Generate HTML coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

Tests use **aiosqlite** in-memory SQLite — no external services needed.

---

## Deployment Guide

### Staging

Push to the `develop` branch — the GitHub Actions workflow automatically:

1. Lints with `ruff`
2. Runs pytest (≥80% coverage required)
3. Scans with `bandit` + `trivy`
4. Builds multi-stage Docker images and pushes to GHCR
5. Runs Alembic migrations via OCI Container Instance
6. Updates the OKE deployment with a rolling update

### Production

Push to `main` (or merge a PR). Same pipeline with an additional manual approval gate (`environment: production`) configured in GitHub repository settings.

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `OCI_USER_OCID` | OCI user OCID |
| `OCI_FINGERPRINT` | API key fingerprint |
| `OCI_TENANCY_OCID` | OCI tenancy OCID |
| `OCI_REGION` | OCI region (e.g. `ap-mumbai-1`) |
| `OCI_KEY_CONTENT` | PEM private key content |
| `OCI_COMPARTMENT_ID` | Compartment OCID for Container Instances |
| `OKE_CLUSTER_ID_STAGING` | OKE cluster ID (staging) |
| `OKE_CLUSTER_ID_PROD` | OKE cluster ID (production) |
| `STAGING_DATABASE_URL` | Postgres URL for staging |
| `PROD_DATABASE_URL` | Postgres URL for production |
| `STAGING_JWT_SECRET` | JWT secret for staging |
| `PROD_JWT_SECRET` | JWT secret for production |
| `SLACK_BOT_TOKEN` | Slack bot token for deploy notifications |
| `SLACK_DEPLOY_CHANNEL` | Slack channel ID |
| `CODECOV_TOKEN` | Codecov upload token |

### Alembic — Manual Migration

```bash
# Create a new migration
alembic revision --autogenerate -m "add_column_x_to_y"

# Apply
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Show current revision
alembic current
```

---

## Security

| Concern | Implementation |
|---------|----------------|
| **Authentication** | JWT Bearer token verified on every request |
| **RBAC** | `require_customer` / `require_admin` FastAPI dependencies |
| **Secrets** | OCI Vault in production; `.env` file locally (never committed) |
| **HTTPS** | TLS terminated at Traefik/nginx ingress with cert-manager |
| **SQL injection** | SQLAlchemy ORM with parameterised queries only |
| **Input validation** | Pydantic v2 strict validation on all endpoints |
| **Non-root container** | Dockerfile creates `appuser`; all commands run as that user |
| **CVE scanning** | `trivy` filesystem scan in CI; `pip-audit` on PRs |
| **SAST** | `bandit` runs on every CI build |

---

## Background Tasks

### Abandoned Cart Recovery (Celery Beat)

- **Schedule**: Every 6 hours (configurable via `CART_RECOVERY_CRON_HOUR`)
- **Logic**: Queries carts with `last_activity_at < NOW() - ABANDONED_CART_HOURS` and `recovery_email_sent_at IS NULL`
- **Action**: POSTs cart list to Notification Service → marks carts as emailed
- **Retry**: 3 attempts with 5-minute back-off

### Invoice PDF Generation (Celery Task)

- **Trigger**: Called asynchronously when `POST /api/v1/invoices` is hit
- **Logic**: Builds GST-compliant PDF with ReportLab → uploads to OCI Object Storage → updates invoice record with `pdf_url` and `status=generated`
- **Retry**: 3 attempts with 60-second back-off

---

*© Nut Meals Pvt. Ltd. — Internal Engineering Documentation*
