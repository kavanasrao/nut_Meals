"""ORM models for carriers and carrier-level serviceability metadata."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CarrierCode(str, enum.Enum):
    DELHIVERY = "delhivery"
    INDIA_POST = "india_post"


class Carrier(Base):
    """A shipping carrier onboarded with the platform."""

    __tablename__ = "carriers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[CarrierCode] = mapped_column(Enum(CarrierCode), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Rules-engine inputs (updated periodically by ops / analytics jobs)
    avg_cost_per_kg: Mapped[float] = mapped_column(Float, default=0.0)
    avg_delivery_hours: Mapped[float] = mapped_column(Float, default=0.0)
    reliability_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1, derived from SLA history

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
