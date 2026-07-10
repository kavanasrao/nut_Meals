"""
ORM models for Returns Management. This service stores the admin-facing
workflow state for a return; the source-of-truth order/shipment data
lives in the Orders and Logistics services and is fetched via their
internal APIs (see app/services/orders_client.py, logistics_client.py).
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common import ReturnStatus, ReturnTier, TimestampMixin, UUIDPrimaryKeyMixin


class ReturnRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An admin-tracked record of a customer return request."""

    __tablename__ = "return_requests"
    __table_args__ = (
        Index("ix_return_requests_status", "status"),
        Index("ix_return_requests_order_id", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    order_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[ReturnStatus] = mapped_column(default=ReturnStatus.PENDING, nullable=False)
    tier: Mapped[ReturnTier] = mapped_column(default=ReturnTier.A, nullable=False)

    refund_amount: Mapped[Optional[Numeric]] = mapped_column(Numeric(10, 2), nullable=True)
    restock_required: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Logistics linkage (pickup/shipment reference from the Logistics service)
    logistics_reference: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    decided_by_admin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    events: Mapped[list["ReturnEvent"]] = relationship(
        back_populates="return_request", cascade="all, delete-orphan", order_by="ReturnEvent.created_at"
    )


class ReturnEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Audit trail entry for state transitions on a ReturnRequest."""

    __tablename__ = "return_events"

    return_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("return_requests.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[Optional[ReturnStatus]] = mapped_column(nullable=True)
    to_status: Mapped[ReturnStatus] = mapped_column(nullable=False)
    actor_admin_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    return_request: Mapped["ReturnRequest"] = relationship(back_populates="events")
