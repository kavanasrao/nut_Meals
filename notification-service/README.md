# Unified Notification & Messaging Service

Part of the nut_Meals microservices backend. Owns all outbound customer/
partner communication: order/payment/delivery event notifications, and
reliable multi-channel messaging (email, SMS, WhatsApp, webhooks) with
an Outbox pattern, exponential-backoff retries, and a Dead Letter Queue.

## Architecture

```
Domain services (order, payment, delivery)
        │  POST /api/v1/notifications/trigger  (fire-and-forget event)
        ▼
┌───────────────────────────────────────────────────────────┐
│  FastAPI API layer (RBAC-gated)                            │
│    /notifications  /messages  /dlq  /audit                 │
└───────────────────────────────────────────────────────────┘
        │  same DB transaction
        ▼
   messages table  +  outbox_events table   (Outbox Pattern)
        │
        │  Celery beat: relay_outbox_task (poll every 10s)
        ▼
   Celery queue "dispatch" → dispatch_message_task
        │
        ▼
   Channel adapter (email / sms / whatsapp / webhook)
        │
   success ──► status=sent, audit log
   retryable failure ──► status=failed, next_retry_at (exp backoff)
   permanent failure / retries exhausted ──► dead_letters table (DLQ)
```

* **Outbox Pattern** (`app/models/outbox.py`, `app/services/outbox_service.py`):
  the domain "intent to notify" and the outbound message row are written
  in one local transaction, so a crash right after commit can't lose a
  notification. A Celery Beat task relays unpublished rows into the
  dispatch queue.
* **Retry Engine** (`app/core/retry_policy.py`): exponential backoff with
  jitter, capped, configurable per channel via the `retry_policies` table.
  Our own retry state lives in Postgres (`next_retry_at`) rather than
  relying on Celery's built-in retry, so retries survive worker restarts
  and are auditable.
* **DLQ** (`app/models/dlq.py`, `app/api/v1/dlq.py`): messages that fail
  permanently or exhaust `max_retries` are moved to `dead_letters`.
  `messaging_admin` users can inspect and `POST /dlq/{id}/reprocess` to
  requeue.
* **Audit & Compliance** (`app/models/audit.py`, `app/api/v1/audit.py`):
  every send/failure/retry/DLQ/reprocess action is appended to
  `audit_logs`. `auditor` role can export CSV/JSON compliance reports.

## Local development

```bash
cp .env.example .env
docker compose up --build
# API:      http://localhost:8010/docs
# Postgres: localhost:5433
# Redis:    localhost:6380
```

Run migrations:
```bash
docker compose exec notification-api alembic upgrade head
```

## Testing

```bash
pip install -r requirements.txt
pytest   # runs with --cov=app --cov-fail-under=80 (see pytest.ini)
```

42 tests covering: outbox idempotency, retry backoff math, dispatcher
success/retry/DLQ paths, channel adapters, RBAC enforcement on every
endpoint, DLQ reprocessing, and audit/compliance export. Current
coverage: ~85%.

## RBAC roles

| Role               | Access                                                   |
|--------------------|-----------------------------------------------------------|
| `notifier`         | Trigger notifications, create messages, read own messages |
| `messaging_admin`  | Full read/write, DLQ reprocessing                          |
| `auditor`          | Read audit logs, export compliance reports                |
| `support`          | Read-only message status lookup                            |

## Security

* JWT bearer auth (`app/core/security.py`) — roles embedded in token claims.
* Production secrets (SMTP, Twilio, WhatsApp) are resolved from **OCI
  Vault** at container startup (`load_secrets_from_vault`), never
  committed to `.env`.
* `HTTPSRedirectMiddleware` + `TrustedHostMiddleware` enforced when
  `ENVIRONMENT=production`.
* Outbound webhooks are HMAC-signed (`X-NutMeals-Signature`).

## CI/CD

`.github/workflows/notification-service-ci.yml`:
1. Lint (ruff, black)
2. Test against real Postgres + Redis services, coverage gate at 80%
3. Multi-arch (amd64 + arm64) Docker build & push via Buildx/QEMU to
   GHCR on `main`/`develop`
4. Deploy step (placeholder — wire to your orchestrator)

## Directory layout

```
app/
  models/        SQLAlchemy ORM (Message, OutboxEvent, DeadLetter, AuditLog, RetryPolicy)
  schemas/       Pydantic request/response models
  channels/      Email / SMS / WhatsApp / Webhook adapters (BaseChannel interface)
  core/          security (JWT + Vault), rbac, retry_policy
  services/      outbox_service, dispatcher, audit_service
  workers/       celery_app, tasks (dispatch/relay/retry/DLQ)
  api/v1/        notifications, messages, dlq, audit routers
alembic/         migrations
tests/           pytest suite (≥80% coverage)
```
