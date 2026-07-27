import uuid
from typing import Optional

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import (
    LedgerEntrySource,
    LedgerEntryType,
    TimestampMixin,
    UUIDPKMixin,
    VendorStatus,
)


class Vendor(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "vendors"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    legal_name: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    tax_id: Mapped[Optional[str]] = mapped_column(String(100))
    address: Mapped[Optional[str]] = mapped_column(Text)
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(100))
    bank_ifsc: Mapped[Optional[str]] = mapped_column(String(20))
    payment_terms_days: Mapped[int] = mapped_column(default=30, nullable=False)
    status: Mapped[VendorStatus] = mapped_column(
        Enum(VendorStatus, name="vendor_status"),
        default=VendorStatus.ACTIVE,
        nullable=False,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(  # noqa: F821
        back_populates="vendor"
    )
    ledger_entries: Mapped[list["VendorLedgerEntry"]] = relationship(
        back_populates="vendor", cascade="all, delete-orphan"
    )


class VendorLedgerEntry(Base, UUIDPKMixin, TimestampMixin):
    """
    Append-only ledger of vendor financial movements. Mirrored/synced to the
    Finance Service for double-entry bookkeeping (see services/ledger_service.py).
    """

    __tablename__ = "vendor_ledger_entries"

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False, index=True
    )
    entry_type: Mapped[LedgerEntryType] = mapped_column(
        Enum(LedgerEntryType, name="ledger_entry_type"), nullable=False
    )
    source: Mapped[LedgerEntrySource] = mapped_column(
        Enum(LedgerEntrySource, name="ledger_entry_source"), nullable=False
    )
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, comment="e.g. purchase_invoice_id"
    )
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    balance_after: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    finance_service_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    finance_service_ref: Mapped[Optional[str]] = mapped_column(String(100))

    vendor: Mapped["Vendor"] = relationship(back_populates="ledger_entries")
