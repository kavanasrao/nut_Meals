"""Shared pytest fixtures for the User Service test suite.

Integration tests run against a real Postgres instance (see the
`postgres-test` service in CI) because several models use Postgres-specific
types (UUID, JSONB, native ENUM) that aren't representable in SQLite. Each
test runs inside a transaction that is rolled back afterward, so tests are
isolated and the schema only needs to be created once per session.

Background-task side effects (OTP delivery, password reset emails, login
alerts) are stubbed out via the `stub_notification_tasks` autouse fixture so
tests never need a live Celery broker or Notification Service — they just
assert the task *would* have been triggered with the right arguments.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole
from main import app

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://nutmeals:nutmeals@localhost:5434/user_db_test",
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, future=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncSession:
    """Yields a session bound to a SAVEPOINT that's rolled back after the
    test, so tests never leak state into one another."""
    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def client(db_session) -> AsyncClient:
    """An httpx AsyncClient wired to the FastAPI app with the DB dependency
    overridden to use the per-test transactional session."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def stub_notification_tasks(monkeypatch):
    """Replace Celery `.delay(...)` calls with in-memory recorders so tests
    never need a live broker or reach out over the network."""
    calls: dict[str, list[dict]] = {"otp": [], "reset": [], "login_alert": []}

    def _record(bucket):
        def _fn(**kwargs):
            calls[bucket].append(kwargs)

        return _fn

    monkeypatch.setattr(
        "app.services.auth_service.send_otp_task.delay", _record("otp")
    )
    monkeypatch.setattr(
        "app.services.auth_service.send_password_reset_email_task.delay", _record("reset")
    )
    monkeypatch.setattr(
        "app.services.auth_service.send_login_alert_task.delay", _record("login_alert")
    )
    return calls


# ── Factories / helpers ──────────────────────────────────────────────────────

async def create_user(
    db_session: AsyncSession,
    *,
    email: str = "jane@example.com",
    password: str = "SuperSecret123",
    phone: str | None = None,
    role: UserRole = UserRole.USER,
    is_blocked: bool = False,
) -> User:
    user = User(
        id=uuid.uuid4(),
        name="Jane Doe",
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        role=role,
        is_blocked=is_blocked,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def auth_headers(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


def future(seconds: int = 300) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


@pytest_asyncio.fixture
async def user(db_session: AsyncSession) -> User:
    return await create_user(db_session)


@pytest_asyncio.fixture
async def admin(db_session: AsyncSession) -> User:
    return await create_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
