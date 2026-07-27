"""Shared pytest fixtures."""
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.db.session import get_db
from app.models.base import Base
from app.core.security import get_current_user, TokenPayload

# ── In-memory SQLite for tests ─────────────────────────────────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False, future=True)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSession() as session:
        yield session


def _make_user(roles=None):
    return TokenPayload(
        user_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        roles=roles or ["customer"],
        email="test@example.com",
    )


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with DB and auth overrides."""

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: _make_user()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with admin role."""

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: _make_user(roles=["admin"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PRODUCT_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
