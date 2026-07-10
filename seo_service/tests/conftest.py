"""
Shared pytest fixtures.

Uses an in-memory SQLite database (via aiosqlite) for fast, isolated
unit/integration tests instead of spinning up real Postgres — schema
is created directly from the ORM metadata per test function. RBAC is
bypassed by overriding `get_current_user`/`require_roles` dependencies
with fixture-controlled fake users, so tests exercise route logic
without needing real signed JWTs.
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import models  # noqa: F401 ensure models are registered
from app.core.security import CurrentUser, Role, get_current_user
from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_maker = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session


@pytest.fixture
def admin_user() -> CurrentUser:
    return CurrentUser(subject="admin-user-1", role=Role.ADMIN, raw_claims={})


@pytest.fixture
def viewer_user() -> CurrentUser:
    return CurrentUser(subject="viewer-user-1", role=Role.VIEWER, raw_claims={})


@pytest_asyncio.fixture
async def client(db_session, admin_user) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated test client (admin role) with the DB dependency overridden."""

    async def _get_db_override():
        yield db_session

    async def _get_current_user_override():
        return admin_user

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = _get_current_user_override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def anon_client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Unauthenticated test client for endpoints that don't require auth."""

    async def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
