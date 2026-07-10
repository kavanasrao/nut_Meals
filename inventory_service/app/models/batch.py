"""Production batch models: tracks turning BOM components into finished stock."""
import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from app.models.mixins import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class BatchStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ProductionBatch(UUIDPKMixin, TimestampMixin, Base):
    """A single manufacturing run: consumes BOM components from a source
    warehouse and, on completion, yields finished product stock."""
    __tablename__ = "production_batches"

    batch_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    bom_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("bill_of_materials.id"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("warehouses.id"), nullable=False
    )
    planned_quantity: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    actual_yield_quantity: Mapped[float | None] = mapped_column(Numeric(14, 3), nullable=True)
    lot_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[BatchStatus] = mapped_column(
        Enum(BatchStatus), nullable=False, default=BatchStatus.PLANNED
    )
    scheduled_start: Mapped["object"] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped["object"] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped["object"] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)

    bom: Mapped["object"] = relationship("BillOfMaterial")
    warehouse: Mapped["object"] = relationship("Warehouse")
