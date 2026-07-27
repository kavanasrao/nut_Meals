# nut_meals User Service

Accounts, authentication, profiles, saved addresses, preferences, and audit
logs for the Nutmeals platform.

## Features

- **Core auth**: register, email+password login, JWT access/refresh tokens.
- **Forgot / reset password**: single-use, hashed, time-limited reset tokens
  delivered by email via the Notification Service; generic responses (no
  account-enumeration).
- **OTP login**: 6-digit codes over SMS or Email, hashed at rest, rate-limited
  by attempt count, auto-provisions a passwordless account on first use.
- **Google Sign-In**: verifies the client-supplied Google ID token against
  Google's `tokeninfo` endpoint (audience-checked against `GOOGLE_CLIENT_ID`),
  links or creates a user, and issues our own JWTs.
- **Profile CRUD**: name, phone, bio, avatar (`profile_picture`), last-login
  tracking.
- **Saved addresses**: full CRUD, `is_default` invariant enforced at the
  service layer (exactly one default; auto-promotes a replacement on delete).
- **Preferences**: language, currency, dark mode, marketing opt-in, and
  per-channel notification toggles.
- **Audit logs**: append-only trail of profile/address/preference/auth
  events, queryable by the user themselves (`/audit/me`) or by an admin for
  any user (`/audit/{user_id}`).
- **RBAC**: local `user`/`admin` role gate (`app/core/rbac.py`) for
  admin-only endpoints; defers to security-service's RBAC for
  cross-service, fine-grained permissions if/when that's needed.
- **Integrations**: Orders Service (order history proxy), CRM Service
  (customer timeline proxy + event push), Notification Service (all
  outbound OTP/email/SMS delivery).

## Architecture

```
app/
  main.py                  FastAPI app, router wiring, health probe
  core/
    config.py               Settings (env-driven; secrets from OCI Vault in prod)
    db.py                    Async SQLAlchemy engine/session
    redis.py                 Async Redis client (profile cache)
    security.py              Password hashing (bcrypt) + JWT encode/decode
    rbac.py                  require_role/require_admin dependency
  auth/
    dependencies.py          get_current_user / require_active_user
  models/                    ORM models: user, otp, password_reset,
                              social_account, address, preference, audit_log
  schemas/                   Pydantic request/response schemas
  services/                  Business logic (one service per domain)
  api/routes/                FastAPI routers
  integrations/               HTTP clients for Notification/Order/CRM services
  tasks/                     Celery app + background delivery tasks
alembic/                     DB migrations (async env, autogenerate-ready)
tests/                       pytest suite (>=80% coverage gate)
```

## Environment variables

See `.env.example` for the full, documented list. Highlights:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres, **must** use the `postgresql+asyncpg://` scheme |
| `REDIS_URL` | Profile cache |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Celery (separate Redis DBs from cache) |
| `JWT_SECRET` / `JWT_ALGORITHM` | Shared with API Gateway for token verification |
| `PASSWORD_RESET_TOKEN_TTL_MINUTES` | Reset link validity window |
| `OTP_LENGTH` / `OTP_TTL_SECONDS` / `OTP_MAX_ATTEMPTS` | OTP login tuning |
| `GOOGLE_CLIENT_ID` | Must match the `aud` claim of Google ID tokens |
| `NOTIFICATION_SERVICE_URL` / `ORDER_SERVICE_URL` / `CRM_SERVICE_URL` | Downstream service base URLs |
| `INTERNAL_SERVICE_TOKEN` | Shared secret for service-to-service calls |

In staging/production, secrets (`JWT_SECRET`, `INTERNAL_SERVICE_TOKEN`,
`GOOGLE_CLIENT_ID`, DB credentials) are injected from **OCI Vault** at
deploy time and are never committed to source control.

## Database schema (new in this change)

| Table | Purpose |
|---|---|
| `otp_codes` | Hashed OTP codes, attempt-limited, TTL-bound |
| `password_reset_tokens` | Hashed single-use reset tokens |
| `social_accounts` | Linked Google accounts (`provider`, `provider_user_id`) |
| `addresses` | Saved addresses, one `is_default` per user |
| `user_preferences` | 1:1 with `users`, language/theme/marketing/notifications |
| `user_audit_logs` | Append-only event trail (nullable `user_id` for pre-auth events like failed lookups) |

Run migrations:

```bash
alembic upgrade head          # apply
alembic revision --autogenerate -m "..."   # generate a new migration
```

Locally (`ENVIRONMENT=local`), the app also calls `Base.metadata.create_all`
at startup as a convenience — this is skipped outside `local`, where Alembic
is the single source of truth for schema changes.

## API summary

All routes are mounted under `/api/v1`. Interactive docs at `/docs` when
`DEBUG=true` (Swagger/OpenAPI is generated automatically by FastAPI from the
route/schema type hints — no separate spec to maintain).

```
POST   /users/register
POST   /users/login
POST   /users/refresh
GET    /users/me
PATCH  /users/me
POST   /users/me/change-password
GET    /users, /users/stats, /users/{id}
PATCH  /users/{id}/block | /unblock

POST   /auth/forgot-password
POST   /auth/reset-password
POST   /auth/otp/request
POST   /auth/otp/verify
POST   /auth/google

GET|POST      /addresses
GET|PATCH|DELETE /addresses/{id}
PATCH         /addresses/{id}/default

GET|PATCH     /preferences

GET           /audit/me
GET           /audit/{user_id}          (admin only)

GET           /me/orders                (proxied — Order Service)
GET           /me/timeline              (proxied — CRM Service)
```

### Internal (service-to-service) endpoints

Not in the public OpenAPI docs (`include_in_schema=False`); gated by
`X-Internal-Service-Token` instead of user JWTs. These are how saved
addresses get **linked to orders and shipments**: the Order Service copies
the returned snapshot onto its own order at checkout time, and the
Logistics Service does the same for a shipment — neither service holds a
live foreign key into this service's `addresses` table, since a user can
edit or delete a saved address after an order has already shipped without
retroactively changing that historical order/shipment.

```
GET  /internal/addresses/{address_id}            snapshot by ID
GET  /internal/users/{user_id}/default-address    snapshot of the user's default address
GET  /internal/users/{user_id}/addresses          all snapshots for a user
```

## Background tasks (Celery)

Worker: `celery -A app.tasks.celery_app worker --loglevel=info -Q user_service`

- `send_otp_task` — deliver OTP via SMS/Email
- `send_password_reset_email_task` — deliver reset link
- `send_login_alert_task` — best-effort new-sign-in notice

All three call the Notification Service's `/api/v1/notifications/trigger`
endpoint, which itself persists to an outbox and retries deliveries — these
Celery retries only cover the User Service → Notification Service hop.

## Running locally

```bash
cp .env.example .env   # then edit as needed
docker compose up --build user-service user-worker postgres redis
alembic upgrade head
```

## Testing

```bash
pip install -r requirements.txt
export TEST_DATABASE_URL=postgresql+asyncpg://nutmeals:nutmeals@localhost:5434/user_db_test
alembic upgrade head
pytest   # runs with --cov=app --cov-fail-under=80 (see pytest.ini)
```

CI (`.github/workflows/user-service-ci.yml`) spins up ephemeral
Postgres/Redis containers, runs lint → migrate → test → build/push a
multi-arch image → deploy placeholder, gated on `main`.

## Security notes

- Passwords hashed with bcrypt (`passlib`); OTPs and reset tokens hashed
  with SHA-256 (high-entropy, single-use, short-TTL secrets — a fast hash is
  appropriate here, unlike user-chosen passwords).
- Forgot-password responses are identical whether or not the email exists.
- OTP verification is attempt-limited (`OTP_MAX_ATTEMPTS`) and TTL-bound.
- Google ID tokens are audience-checked against `GOOGLE_CLIENT_ID` before
  trust.
- All service-to-service calls to Notification/Order/CRM services carry
  `X-Internal-Service-Token` and are fail-soft (a downstream outage never
  fails the caller's own request), except password-reset/OTP delivery which
  surfaces failures via Celery retries since delivery there is essential.
- HTTPS termination is expected at the API Gateway / ingress; `ENFORCE_HTTPS`
  is available for services that terminate TLS themselves.
