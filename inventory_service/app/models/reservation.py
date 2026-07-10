"""Inventory reservation models — hold stock for an order pending payment."""
import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from app.models.mixins import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class ReservationStatus(str, enum.Enum):
    ACTIVE = "active"
    CONFIRMED = "confirmed"   # payment succeeded -> stock permanently deducted
    RELEASED = "released"     # expired or cancelled -> stock returned to available
    EXPIRED = "expired"


class StockReservation(UUIDPKMixin, TimestampMixin, Base):
    """A hold placed against `quantity_reserved` on a StockLevel row.

    Created when the Orders service asks Inventory to reserve stock for a
    pending checkout. If payment does not confirm within
    settings.RESERVATION_TTL_SECONDS, a Celery beat task releases it.
    """
    __tablename__ = "stock_reservations"

    order_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("items.id"), nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("warehouses.id"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus), nullable=False, default=ReservationStatus.ACTIVE
    )
    expires_at: Mapped["object"] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped["object"] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped["object"] = mapped_column(DateTime(timezone=True), nullable=True)

    item: Mapped["object"] = relationship("Item")
    warehouse: Mapped["object"] = relationship("Warehouse")
