import asyncio
import os
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://procurement:procurement@localhost:5432/procurement_test_db",
)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("FINANCE_SERVICE_API_KEY", "test-key")

from app.core.security import CurrentUser, get_current_user  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.finance_client import FinanceServiceClient  # noqa: E402
import app.models  # noqa: E402,F401

TEST_DATABASE_URL = os.environ["DATABASE_URL"]

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=None)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()
        # clean all tables between tests for isolation
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


@pytest.fixture
def admin_user() -> CurrentUser:
    return CurrentUser(id=uuid.uuid4(), email="admin@nutmeals.test", roles=["procurement_admin"])


@pytest.fixture
def officer_user() -> CurrentUser:
    return CurrentUser(id=uuid.uuid4(), email="officer@nutmeals.test", roles=["procurement_officer"])


@pytest.fixture
def mock_finance_client() -> AsyncMock:
    mock = AsyncMock(spec=FinanceServiceClient)
    mock.post_journal_entry.return_value = "FIN-REF-12345"
    return mock


@pytest_asyncio.fixture
async def client(db_session, admin_user, mock_finance_client) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
