"""Shared pytest fixtures: in-memory-ish async DB, fake redis, fake adapters."""
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.adapters.base import ServiceabilityResult, ShipmentBookingResult, TrackingUpdate
from app.database import Base, get_db
from app.main import app
from app.models.carrier import Carrier, CarrierCode

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, future=True)
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
async def seeded_carriers(db_session: AsyncSession):
    delhivery = Carrier(
        id=uuid.uuid4(),
        code=CarrierCode.DELHIVERY,
        name="Delhivery",
        is_active=True,
        avg_cost_per_kg=18,
        avg_delivery_hours=48,
        reliability_score=0.9,
    )
    india_post = Carrier(
        id=uuid.uuid4(),
        code=CarrierCode.INDIA_POST,
        name="India Post",
        is_active=True,
        avg_cost_per_kg=12,
        avg_delivery_hours=96,
        reliability_score=0.7,
    )
    db_session.add_all([delhivery, india_post])
    await db_session.commit()
    return {"delhivery": delhivery, "india_post": india_post}


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class FakeAdapter:
    """Configurable stand-in for BaseCarrierAdapter used across unit tests."""

    def __init__(
        self,
        code: str,
        serviceable: bool = True,
        cost: float = 50.0,
        hours: float = 48.0,
        booking_should_fail: bool = False,
        awb: str = "FAKEAWB123",
    ):
        self.code = code
        self._serviceable = serviceable
        self._cost = cost
        self._hours = hours
        self._booking_should_fail = booking_should_fail
        self._awb = awb

    async def check_serviceability(self, origin_pincode, destination_pincode, weight_kg):
        return ServiceabilityResult(self._serviceable, self._cost, self._hours)

    async def create_shipment(self, order_id, origin_pincode, destination_pincode, weight_kg, cod_amount):
        from app.adapters.base import CarrierAPIError

        if self._booking_should_fail:
            raise CarrierAPIError(f"{self.code} booking simulated failure")
        return ShipmentBookingResult(carrier_awb=self._awb, label_url="http://label.test/x", raw_response={"ok": True})

    async def create_reverse_pickup(self, awb, pickup_pincode, reason, weight_kg):
        return ShipmentBookingResult(carrier_awb=f"REV-{awb}", label_url=None, raw_response={"ok": True})

    async def fetch_tracking(self, awb):
        return [
            TrackingUpdate(
                status="delivered",
                location="Bengaluru Hub",
                remarks="Delivered to recipient",
                event_time=datetime.now(timezone.utc),
                raw_payload={"raw": True},
            )
        ]


@pytest.fixture
def fake_adapter_factory():
    return FakeAdapter
