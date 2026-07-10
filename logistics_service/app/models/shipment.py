"""ORM models for shipments, tracking events and reverse pickups."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ShipmentStatus(str, enum.Enum):
    CREATED = "created"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    RTO = "return_to_origin"
    CANCELLED = "cancelled"


class ShipmentType(str, enum.Enum):
    FORWARD = "forward"
    REVERSE = "reverse"


class Shipment(Base):
    """A forward or reverse shipment tied to an order."""

    __tablename__ = "shipments"
    __table_args__ = (Index("ix_shipments_order_id", "order_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    carrier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("carriers.id"), nullable=False)
    carrier_awb: Mapped[str] = mapped_column(String(64), nullable=True, unique=True)

    shipment_type: Mapped[ShipmentType] = mapped_column(Enum(ShipmentType), default=ShipmentType.FORWARD)
    status: Mapped[ShipmentStatus] = mapped_column(Enum(ShipmentStatus), default=ShipmentStatus.CREATED)

    origin_pincode: Mapped[str] = mapped_column(String(10), nullable=False)
    destination_pincode: Mapped[str] = mapped_column(String(10), nullable=False)

    weight_kg: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    cod_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    meta: Mapped[dict] = mapped_column(JSON, default=dict)  # carrier-specific payload/response

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tracking_events: Mapped[list["TrackingEvent"]] = relationship(
        back_populates="shipment",
        cascade="all, delete-orphan",
        order_by="TrackingEvent.event_time",
        lazy="selectin",
    )


class TrackingEvent(Base):
    """An individual tracking checkpoint reported by a carrier."""

    __tablename__ = "tracking_events"
    __table_args__ = (Index("ix_tracking_events_shipment_id", "shipment_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shipments.id"), nullable=False)

    status: Mapped[ShipmentStatus] = mapped_column(Enum(ShipmentStatus), nullable=False)
    location: Mapped[str] = mapped_column(String(128), nullable=True)
    remarks: Mapped[str] = mapped_column(String(255), nullable=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    shipment: Mapped["Shipment"] = relationship(back_populates="tracking_events")
