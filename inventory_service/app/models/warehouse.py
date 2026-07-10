"""Warehouse and per-warehouse stock level models."""
import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint, func
from app.models.mixins import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class MovementType(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    PRODUCTION_CONSUME = "production_consume"
    PRODUCTION_YIELD = "production_yield"
    RESERVATION_HOLD = "reservation_hold"
    RESERVATION_RELEASE = "reservation_release"
    ADJUSTMENT = "adjustment"


class Warehouse(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "warehouses"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str] = mapped_column(String(256), nullable=False)
    capacity_units: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)

    stock_levels: Mapped[list["StockLevel"]] = relationship(
        back_populates="warehouse", cascade="all, delete-orphan"
    )


class Item(UUIDPKMixin, TimestampMixin, Base):
    """A stock-keeping unit: raw ingredient, component, or finished product."""
    __tablename__ = "items"

    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(16), nullable=False, default="unit")
    is_finished_product: Mapped[bool] = mapped_column(default=False)
    reorder_threshold: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)


class StockLevel(UUIDPKMixin, TimestampMixin, Base):
    """Quantity of an item on hand at a specific warehouse, split into
    available vs reserved so reservations never oversell stock."""
    __tablename__ = "stock_levels"
    __table_args__ = (UniqueConstraint("warehouse_id", "item_id", name="uq_stock_wh_item"),)

    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    quantity_on_hand: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    quantity_reserved: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)

    warehouse: Mapped["Warehouse"] = relationship(back_populates="stock_levels")
    item: Mapped["Item"] = relationship()

    @property
    def quantity_available(self) -> float:
        return float(self.quantity_on_hand) - float(self.quantity_reserved)


class StockTransfer(UUIDPKMixin, TimestampMixin, Base):
    """A movement of stock from one warehouse to another."""
    __tablename__ = "stock_transfers"

    item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("items.id"), nullable=False)
    source_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("warehouses.id"), nullable=False
    )
    destination_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("warehouses.id"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    lot_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    initiated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="completed")


class StockMovementLog(UUIDPKMixin, Base):
    """Immutable audit trail of every stock quantity change, for compliance
    and lot traceability. Never updated or deleted after insert."""
    __tablename__ = "stock_movement_logs"

    timestamp: Mapped["object"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("items.id"), nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("warehouses.id"), nullable=False
    )
    movement_type: Mapped[MovementType] = mapped_column(Enum(MovementType), nullable=False)
    quantity_delta: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    lot_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # e.g. batch/order id
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)
