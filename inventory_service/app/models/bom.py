"""Bill of Materials (BOM) models with versioning support."""
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from app.models.mixins import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class BillOfMaterial(UUIDPKMixin, TimestampMixin, Base):
    """A versioned recipe: which product this BOM produces, and how much
    finished product one production run of this BOM yields."""
    __tablename__ = "bill_of_materials"
    __table_args__ = (
        UniqueConstraint("product_item_id", "version", name="uq_bom_product_version"),
    )

    product_item_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("items.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    yield_quantity: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # latest active version
    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)

    components: Mapped[list["BOMComponent"]] = relationship(
        back_populates="bom", cascade="all, delete-orphan"
    )
    product_item: Mapped["object"] = relationship("Item", foreign_keys=[product_item_id])


class BOMComponent(UUIDPKMixin, Base):
    """A single ingredient/component line within a BOM."""
    __tablename__ = "bom_components"

    bom_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("bill_of_materials.id", ondelete="CASCADE"), nullable=False
    )
    component_item_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("items.id"), nullable=False
    )
    quantity_required: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)

    bom: Mapped["BillOfMaterial"] = relationship(back_populates="components")
    component_item: Mapped["object"] = relationship("Item", foreign_keys=[component_item_id])
