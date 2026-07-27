import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text, Date, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import InvoiceStatus, TimestampMixin, UUIDPKMixin


class PurchaseInvoice(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "purchase_invoices"

    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False, index=True
    )
    purchase_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=True, index=True
    )
    grn_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("goods_receipt_notes.id"), nullable=True
    )
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status"),
        default=InvoiceStatus.RECEIVED,
        nullable=False,
        index=True,
    )
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    amount_paid: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    file_url: Mapped[Optional[str]] = mapped_column(String(500))
    reconciliation_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Uniqueness of (vendor, invoice_number) prevents duplicate booking
    __table_args__ = ()

    items: Mapped[list["PurchaseInvoiceItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class PurchaseInvoiceItem(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "purchase_invoice_items"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_invoices.id"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    tax_rate_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    line_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    invoice: Mapped["PurchaseInvoice"] = relationship(back_populates="items")
