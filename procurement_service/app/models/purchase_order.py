import uuid
from typing import Optional
from datetime import date

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text, Date, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import PurchaseOrderStatus, TimestampMixin, UUIDPKMixin


class PurchaseOrder(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "purchase_orders"

    po_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False, index=True
    )
    status: Mapped[PurchaseOrderStatus] = mapped_column(
        Enum(PurchaseOrderStatus, name="purchase_order_status"),
        default=PurchaseOrderStatus.DRAFT,
        nullable=False,
        index=True,
    )
    expected_delivery_date: Mapped[Optional[date]] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[Optional[str]] = mapped_column(String(50))
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)

    vendor: Mapped["Vendor"] = relationship(back_populates="purchase_orders")  # noqa: F821
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan"
    )
    grns: Mapped[list["GoodsReceiptNote"]] = relationship(  # noqa: F821
        back_populates="purchase_order"
    )


class PurchaseOrderItem(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "purchase_order_items"

    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    tax_rate_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    line_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="items")
