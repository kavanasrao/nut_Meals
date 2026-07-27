"""
GST (Goods & Services Tax) computation models.

nut_Meals sells physical, tangible goods (packaged nuts/snacks) in India, so
every invoice must carry GST computed against the correct rate for each
product's tax category. Two concerns are modelled separately:

  1. `GSTRate` - a versioned rate card: which GST% applies to which product
     category, valid over an effective date range. Owned by Finance (not a
     copy of the Catalog service's product taxonomy); Order/Catalog services
     pass a `category_code` string when requesting GST computation, and
     Finance validates it against this table.
  2. `GSTInvoice` / `GSTInvoiceLine` - the computed result for a specific
     order. Storing the computed amounts (rather than re-deriving them from
     the rate card on every read) is deliberate: GST rates change over time,
     but a historical invoice must always show the rate that applied on the
     day it was raised (tax audit requirement).

Tax split rules (standard Indian GST):
  - Intra-state supply (seller and customer in the same state): the total
    rate is split evenly into CGST (Central GST) + SGST (State GST).
  - Inter-state supply: the full rate is charged as IGST (Integrated GST).

All monetary amounts are BigInteger in the smallest currency unit (minor
units / paise for INR), consistent with the rest of the ledger.
"""

import enum
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class GSTInvoiceStatus(str, enum.Enum):
    DRAFT = "draft"  # computed but not yet posted to the ledger
    POSTED = "posted"  # ledger entry created; amounts are now immutable
    CANCELLED = "cancelled"  # invoice voided before posting (e.g. order cancelled same-day)


class GSTRate(TimestampMixin, Base):
    """
    Versioned GST rate card. `rate_basis_points` is the *total* GST rate
    (e.g. 500 = 5.00%, 1800 = 18.00%); the CGST/SGST/IGST split is computed
    at invoice time depending on whether the supply is intra- or
    inter-state. Basis points (1/100 of a percent) avoid floating point
    error, mirroring the minor-unit convention used for amounts.
    """

    __tablename__ = "gst_rates"
    __table_args__ = (
        UniqueConstraint("category_code", "effective_from", name="uq_gst_rate_category_effective_from"),
        Index("ix_gst_rates_category", "category_code"),
        Index("ix_gst_rates_active", "is_active"),
        CheckConstraint("rate_basis_points >= 0 AND rate_basis_points <= 10000", name="ck_gst_rate_bp_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_code: Mapped[str] = mapped_column(
        String(50), nullable=False, doc="Product tax category code, e.g. 'RAW_NUTS', 'ROASTED_FLAVORED_NUTS'"
    )
    category_name: Mapped[str] = mapped_column(String(120), nullable=False)
    hsn_code: Mapped[str | None] = mapped_column(
        String(20), nullable=True, doc="Harmonized System of Nomenclature code for the product category"
    )
    rate_basis_points: Mapped[int] = mapped_column(
        Integer, nullable=False, doc="Total GST rate in basis points, e.g. 500 = 5.00%, 1800 = 18.00%"
    )
    effective_from: Mapped[str] = mapped_column(String(10), nullable=False, doc="ISO date YYYY-MM-DD")
    effective_to: Mapped[str | None] = mapped_column(
        String(10), nullable=True, doc="ISO date YYYY-MM-DD; null means still in effect"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)

    invoice_lines: Mapped[list["GSTInvoiceLine"]] = relationship(back_populates="gst_rate")

    def __repr__(self) -> str:
        return f"<GSTRate {self.category_code} {self.rate_basis_points}bp from={self.effective_from}>"


class GSTInvoice(TimestampMixin, Base):
    """
    Header record for a single order's computed GST. One GSTInvoice per
    order_reference (enforced by unique constraint) - re-computation for the
    same order updates the DRAFT record rather than creating a duplicate.
    """

    __tablename__ = "gst_invoices"
    __table_args__ = (
        UniqueConstraint("order_reference", name="uq_gst_invoices_order_reference"),
        Index("ix_gst_invoices_status", "status"),
        Index("ix_gst_invoices_invoice_date", "invoice_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    order_reference: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="Opaque order ID from the Orders service"
    )
    invoice_date: Mapped[str] = mapped_column(String(10), nullable=False, doc="ISO date YYYY-MM-DD")

    seller_state_code: Mapped[str] = mapped_column(String(2), nullable=False, doc="GST state code of the seller")
    customer_state_code: Mapped[str] = mapped_column(String(2), nullable=False, doc="GST state code of the customer")
    is_interstate: Mapped[bool] = mapped_column(
        Boolean, nullable=False, doc="True => IGST applies; False => CGST+SGST split applies"
    )

    taxable_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cgst_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    sgst_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    igst_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_gst_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_invoice_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    status: Mapped[GSTInvoiceStatus] = mapped_column(
        Enum(GSTInvoiceStatus, name="gst_invoice_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=GSTInvoiceStatus.DRAFT,
        nullable=False,
    )
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    posted_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    lines: Mapped[list["GSTInvoiceLine"]] = relationship(
        back_populates="gst_invoice", cascade="all, delete-orphan", order_by="GSTInvoiceLine.line_number"
    )
    credit_notes: Mapped[list["CreditNote"]] = relationship(back_populates="gst_invoice")  # noqa: F821

    def __repr__(self) -> str:
        return f"<GSTInvoice {self.invoice_number} order={self.order_reference} {self.status}>"


class GSTInvoiceLine(TimestampMixin, Base):
    """
    Per-product-category breakdown of a GSTInvoice. `gst_rate_id` pins the
    exact rate row applied (not just the category), so the invoice remains
    reconstructable even after the rate card changes later.
    """

    __tablename__ = "gst_invoice_lines"
    __table_args__ = (
        Index("ix_gst_invoice_lines_invoice", "gst_invoice_id"),
        CheckConstraint("taxable_amount_minor >= 0", name="ck_gst_invoice_line_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gst_invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gst_invoices.id", ondelete="CASCADE"), nullable=False
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    product_reference: Mapped[str | None] = mapped_column(
        String(100), nullable=True, doc="Opaque SKU/product ID from the Catalog service"
    )
    category_code: Mapped[str] = mapped_column(String(50), nullable=False)
    gst_rate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gst_rates.id"), nullable=False)

    taxable_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cgst_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    sgst_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    igst_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    gst_invoice: Mapped["GSTInvoice"] = relationship(back_populates="lines")
    gst_rate: Mapped["GSTRate"] = relationship(back_populates="invoice_lines")

    def __repr__(self) -> str:
        return f"<GSTInvoiceLine {self.category_code} taxable={self.taxable_amount_minor}>"