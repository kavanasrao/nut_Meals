"""
Refund accounting.

A Refund represents money actually flowing back to a customer (or credited
to their wallet/store-credit), as distinct from a CreditNote which merely
reverses invoiced revenue/GST on paper. The two are linked (a credit note's
`refund_id` points here) but track different things:

  - CreditNote: "we owe the customer this much, and here's why" (a paper
    trail + GST reversal).
  - Refund: "we actually paid/credited the customer this much, via this
    method" (a cash-movement + Payments-service integration record).

Refunds always trigger an accounting entry (business rule: "ensure refunds
trigger accounting entries") - see RefundService.record_refund, which posts
DR Customer Refunds Payable / CR Bank-or-Gateway-Clearing (or DR Store
Credit Payable for non-cash refunds) atomically with creating this row.

Integration with the Payments service is asynchronous: `gateway_refund_id`
starts null and is filled in once the Payments service's webhook confirms
the gateway-side refund; `status` transitions accordingly (see
app.tasks.refund_tasks for the reconciliation of pending refunds).
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class RefundStatus(str, enum.Enum):
    INITIATED = "initiated"  # recorded in Finance, accounting entry not yet posted
    ACCOUNTING_POSTED = "accounting_posted"  # ledger entry posted; awaiting gateway confirmation
    GATEWAY_PENDING = "gateway_pending"  # sent to Payments service, awaiting its callback
    COMPLETED = "completed"  # Payments service confirmed the refund reached the customer
    FAILED = "failed"  # gateway rejected/failed the refund; requires manual follow-up


class RefundMethod(str, enum.Enum):
    ORIGINAL_PAYMENT_METHOD = "original_payment_method"
    BANK_TRANSFER = "bank_transfer"
    STORE_CREDIT = "store_credit"
    WALLET = "wallet"


class Refund(TimestampMixin, Base):
    __tablename__ = "refunds"
    __table_args__ = (
        UniqueConstraint("refund_reference", name="uq_refunds_reference"),
        Index("ix_refunds_status", "status"),
        Index("ix_refunds_order_reference", "order_reference"),
        Index("ix_refunds_payment_reference", "payment_reference"),
        CheckConstraint("amount_minor > 0", name="ck_refund_amount_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    refund_reference: Mapped[str] = mapped_column(String(30), nullable=False)
    order_reference: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="Opaque order ID from the Orders service"
    )
    payment_reference: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="Opaque payment ID from the Payments service being refunded"
    )

    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    method: Mapped[RefundMethod] = mapped_column(
        Enum(RefundMethod, name="refund_method_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status: Mapped[RefundStatus] = mapped_column(
        Enum(RefundStatus, name="refund_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=RefundStatus.INITIATED,
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)

    gateway_refund_id: Mapped[str | None] = mapped_column(
        String(120), nullable=True, doc="Payments service / gateway-side refund ID, filled in via webhook"
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    credit_notes: Mapped[list["CreditNote"]] = relationship(  # noqa: F821
        back_populates="refund", foreign_keys="CreditNote.refund_id"
    )

    def __repr__(self) -> str:
        return f"<Refund {self.refund_reference} {self.status} amount={self.amount_minor}>"