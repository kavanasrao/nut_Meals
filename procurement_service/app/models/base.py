"""Shared mixins and enums used across models."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class VendorStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLACKLISTED = "blacklisted"


class PurchaseOrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class GRNStatus(str, enum.Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class InvoiceStatus(str, enum.Enum):
    RECEIVED = "received"
    MATCHED = "matched"
    DISPUTED = "disputed"
    APPROVED_FOR_PAYMENT = "approved_for_payment"
    PAID = "paid"
    CANCELLED = "cancelled"


class LedgerEntryType(str, enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class LedgerEntrySource(str, enum.Enum):
    INVOICE = "invoice"
    PAYMENT = "payment"
    ADJUSTMENT = "adjustment"
    OPENING_BALANCE = "opening_balance"
