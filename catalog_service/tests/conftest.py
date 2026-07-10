"""Shared pytest fixtures.

Tests run against a real PostgreSQL instance (not SQLite) because the models
use Postgres-native types (UUID, JSONB, ENUM) — this is provided either by
docker-compose's `db-test` service locally, or the `postgres:16` service
container in GitHub Actions (see .github/workflows/catalog-ci-cd.yml).
"""
import asyncio
import uuid
from typing import AsyncGenerator

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.core.rbac import Role

settings = get_settings()

TEST_DB_URL = settings.database_url


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DB_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def make_token(role: Role, user_id: str | None = None) -> str:
    """Mint a JWT the same way the identity service would, for tests."""
    payload = {"sub": user_id or str(uuid.uuid4()), "role": role.value}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@pytest.fixture
def admin_headers():
    return {"Authorization": f"Bearer {make_token(Role.CATALOG_ADMIN)}"}


@pytest.fixture
def moderator_headers():
    return {"Authorization": f"Bearer {make_token(Role.MODERATOR)}"}


@pytest.fixture
def customer_headers():
    customer_id = str(uuid.uuid4())
    return {"Authorization": f"Bearer {make_token(Role.CUSTOMER, customer_id)}"}, customer_id


@pytest.fixture
def viewer_headers():
    return {"Authorization": f"Bearer {make_token(Role.VIEWER)}"}
