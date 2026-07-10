"""
Shared pytest fixtures for the Security Service test suite.

Integration tests run against a real Postgres instance (see
docker-compose.test.yml / the `postgres-test` service in CI) because several
models use Postgres-specific types (UUID, JSONB, native ENUM) that aren't
representable in SQLite. Each test runs inside a transaction that is rolled
back afterward, so tests are isolated and the schema only needs to be created
once per session.
"""
import asyncio
import os
import uuid
from datetime import datetime, timedelta

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models.rbac import Permission, Role, RolePermission, UserRoleBinding

settings = get_settings()

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://nutmeals:nutmeals@localhost:5433/security_db_test",
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
    """Yields a session bound to a SAVEPOINT that's rolled back after the test,
    so tests never leak state into one another."""
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


def make_jwt(user_id: str = "user-123", roles: list[str] | None = None) -> str:
    """Build a signed test JWT matching the app's configured secret/algorithm."""
    payload = {
        "sub": user_id,
        "roles": roles or [],
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def auth_headers(user_id: str = "user-123", roles: list[str] | None = None) -> dict:
    return {"Authorization": f"Bearer {make_jwt(user_id, roles)}"}


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> str:
    """Seeds an 'admin' role with every permission this test suite needs, bound
    to user id 'admin-user', and returns that user id for use in auth_headers()."""
    perm_codes = [
        ("waf:manage_rules", "security"),
        ("waf:read", "security"),
        ("audit:write", "security"),
        ("audit:read", "security"),
        ("audit:export", "security"),
        ("compliance:manage", "security"),
        ("compliance:read", "security"),
        ("rbac:manage", "security"),
        ("rbac:read", "security"),
    ]
    permissions = [Permission(code=code, service=svc) for code, svc in perm_codes]
    db_session.add_all(permissions)
    await db_session.flush()

    role = Role(name="test-admin", description="Full-access role for tests")
    role.permissions = permissions
    db_session.add(role)
    await db_session.flush()

    binding = UserRoleBinding(user_id="admin-user", role_id=role.id, granted_by="test-fixture")
    db_session.add(binding)
    await db_session.commit()

    return "admin-user"
