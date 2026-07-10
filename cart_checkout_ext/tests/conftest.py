"""
Shared pytest fixtures for the Cart/Checkout Extensions service.

Tests run against a real PostgreSQL instance (matching production, since
several models use Postgres-specific UUID/JSONB column types) rather than
SQLite. Locally this is provided by `docker-compose -f docker-compose.yml
up -d postgres`; in CI it is a GitHub Actions service container. The DB URL
can be overridden with the TEST_DATABASE_URL env var.
"""
import asyncio
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.security.auth import create_access_token

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/cart_checkout_ext_test",
)

test_engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def customer_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def auth_headers(customer_id):
    token = create_access_token(customer_id=customer_id, roles=["customer"])
    return {"Authorization": f"Bearer {token}"}
