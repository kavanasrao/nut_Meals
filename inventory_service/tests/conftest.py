"""Shared pytest fixtures for the Inventory Service test suite.

Uses an async SQLite engine for fast, isolated unit/integration tests
(the production DB is Postgres; CI also runs a `pytest -m postgres` pass
against a real Postgres service container — see .github/workflows).
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models.warehouse import Item, Warehouse

settings = get_settings()

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def make_token(roles: list[str], subject: str = "test-user") -> str:
    payload = {
        "sub": subject,
        "roles": roles,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def admin_headers():
    return {"Authorization": f"Bearer {make_token(['inventory:admin'])}"}


@pytest.fixture
def manager_headers():
    return {"Authorization": f"Bearer {make_token(['inventory:manager'])}"}


@pytest.fixture
def operator_headers():
    return {"Authorization": f"Bearer {make_token(['inventory:operator'])}"}


@pytest.fixture
def orders_service_headers():
    return {"Authorization": f"Bearer {make_token(['inventory:orders_service'])}"}


@pytest.fixture
def viewer_headers():
    return {"Authorization": f"Bearer {make_token(['inventory:viewer'])}"}


@pytest_asyncio.fixture
async def seeded_warehouse(db_session: AsyncSession) -> Warehouse:
    wh = Warehouse(code="WH-MAIN", name="Main Warehouse", location="Austin, TX", capacity_units=100000)
    db_session.add(wh)
    await db_session.commit()
    await db_session.refresh(wh)
    return wh


@pytest_asyncio.fixture
async def seeded_second_warehouse(db_session: AsyncSession) -> Warehouse:
    wh = Warehouse(code="WH-SECOND", name="Second Warehouse", location="Dallas, TX", capacity_units=50000)
    db_session.add(wh)
    await db_session.commit()
    await db_session.refresh(wh)
    return wh


@pytest_asyncio.fixture
async def seeded_items(db_session: AsyncSession) -> dict[str, Item]:
    almonds = Item(sku="RAW-ALMOND", name="Raw Almonds", unit_of_measure="kg")
    honey = Item(sku="RAW-HONEY", name="Honey", unit_of_measure="kg")
    bar = Item(sku="FIN-NUTBAR", name="Nut Bar", unit_of_measure="unit", is_finished_product=True)
    db_session.add_all([almonds, honey, bar])
    await db_session.commit()
    for i in (almonds, honey, bar):
        await db_session.refresh(i)
    return {"almonds": almonds, "honey": honey, "bar": bar}
