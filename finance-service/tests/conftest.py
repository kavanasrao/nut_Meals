"""
Shared pytest fixtures.

Integration tests run against a real PostgreSQL instance (required because
the models use Postgres-specific UUID/JSONB/ENUM types and CHECK
constraints that SQLite can't emulate faithfully). Set TEST_DATABASE_URL to
point at a disposable test database; docker-compose.yml provides one for
local dev, and the GitHub Actions workflow spins up a `postgres` service
container for CI.

Each test runs inside an outer transaction that is rolled back at the end,
so tests never leak state into one another and the schema only needs to be
created once per test session.
"""

import os
from datetime import UTC, datetime, timedelta

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault(
    "FINANCE_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/finance_test_db",
)
os.environ.setdefault("FINANCE_JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("FINANCE_ENV", "local")

from app.core.config import get_settings  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.core.security import FinanceRole, Principal, get_current_principal  # noqa: E402
from app.main import app  # noqa: E402

settings = get_settings()

test_db_url = settings.DATABASE_URL


@pytest_asyncio.fixture
async def db_session():
    """
    Creates a fresh engine bound to the *current* test's event loop (avoids
    'Future attached to a different loop' errors that occur when an engine
    created in one test's event loop is reused in another), ensures the
    schema exists, and yields a session wrapped in a transaction that is
    rolled back after the test so tests never leak state into one another.
    """
    engine = create_async_engine(test_db_url, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    connection = await engine.connect()
    trans = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()
        await engine.dispose()


def make_token(*, subject: str = "test-user", roles: list[str] | None = None) -> str:
    payload = {
        "sub": subject,
        "roles": roles or [FinanceRole.ADMIN],
        "iss": settings.JWT_ISSUER,
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """An httpx AsyncClient wired to the FastAPI app with DB/auth dependency overrides."""

    async def _override_get_db():
        yield db_session

    async def _override_principal():
        return Principal(subject="test-user", roles=[FinanceRole.ADMIN])

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_principal] = _override_principal

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {make_token()}"}
