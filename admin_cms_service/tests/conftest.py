"""
Shared pytest fixtures for the Admin CMS Service test suite.

Tests run against a real (ephemeral) Postgres database -- see
docker-compose.yml's `db-test` service, or the `postgres` service
container defined in the GitHub Actions workflow -- because several ORM
columns use native Postgres types (UUID, JSONB, ARRAY, INET) that have
no SQLite equivalent.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import Base, engine, get_db
from app.main import app
from app.models.common import AdminRole

settings = get_settings()


@pytest_asyncio.fixture(scope="session")
async def _prepare_database():
    """Create all tables once per test session, drop them at the end."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(_prepare_database) -> AsyncSession:
    """
    Yields a session wrapped in a transaction that is rolled back after
    each test, so tests never leak state into one another.
    """
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """An httpx AsyncClient wired to the FastAPI app with the DB dependency overridden."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


def make_admin_token(
    roles: list[AdminRole], admin_id: uuid.UUID | None = None, email: str = "admin@nutmeals.test"
) -> str:
    """Build a signed JWT matching the shape admin-service would issue."""
    admin_id = admin_id or uuid.uuid4()
    payload = {
        "sub": str(admin_id),
        "email": email,
        "roles": [r.value for r in roles],
        "aud": settings.jwt_audience,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.jwt_public_key, algorithm=settings.jwt_algorithm)


@pytest.fixture
def super_admin_headers() -> dict:
    token = make_admin_token([AdminRole.SUPER_ADMIN])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def content_admin_headers() -> dict:
    token = make_admin_token([AdminRole.CONTENT_ADMIN])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def support_admin_headers() -> dict:
    token = make_admin_token([AdminRole.SUPPORT_ADMIN])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def finance_admin_headers() -> dict:
    token = make_admin_token([AdminRole.FINANCE_ADMIN])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def analytics_viewer_headers() -> dict:
    token = make_admin_token([AdminRole.ANALYTICS_VIEWER])
    return {"Authorization": f"Bearer {token}"}
