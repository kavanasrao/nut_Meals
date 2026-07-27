"""
Credit note workflow.

A credit note is issued when value already invoiced to a customer needs to
be reversed - a return, a damaged-goods claim, a post-sale price adjustment,
or an order cancellation after GST was already posted. It is the compliant
way to reverse revenue/GST without editing or deleting the original invoice
(same "never mutate posted history" principle as journal entry reversal).

Lifecycle:
  DRAFT    -> created, amounts computed, not yet reflected in the ledger.
  ISSUED   -> posted to the ledger (reverses revenue + GST proportionally);
              immutable from this point on.
  APPLIED  -> linked to a Refund that actually pays the money back/credits
              the customer (a credit note does not itself move cash).
  CANCELLED-> voided before issuance (e.g. raised in error).

A credit note may exist for a while in ISSUED state without being APPLIED -
e.g. the credit is only usable against a future order (`store credit`), or
the refund is pending gateway processing.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin
from nut_meals.customer_commerce_service.app.models.invoice import Invoice


class CreditNoteStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    APPLIED = "applied"
    CANCELLED = "cancelled"


class CreditNoteReason(str, enum.Enum):
    RETURN = "return"
    DAMAGED_GOODS = "damaged_goods"
    PRICE_ADJUSTMENT = "price_adjustment"
    ORDER_CANCELLED = "order_cancelled"
    GOODWILL = "goodwill"
    OTHER = "other"


class CreditNote(TimestampMixin, Base):
    __tablename__ = "credit_notes"
    __table_args__ = (
        UniqueConstraint("credit_note_number", name="uq_credit_notes_number"),
        Index("ix_credit_notes_status", "status"),
        Index("ix_credit_notes_order_reference", "order_reference"),
        CheckConstraint("taxable_amount_minor >= 0", name="ck_credit_note_taxable_non_negative"),
        CheckConstraint(
            "total_amount_minor = taxable_amount_minor + cgst_amount_minor + sgst_amount_minor + igst_amount_minor",
            name="ck_credit_note_total_matches_components",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    credit_note_number: Mapped[str] = mapped_column(String(30), nullable=False)
    order_reference: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="Opaque order ID from the Orders service"
    )
    gst_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gst_invoices.id"), nullable=True, doc="Original invoice being credited"
    )

    reason: Mapped[CreditNoteReason] = mapped_column(
        Enum(CreditNoteReason, name="credit_note_reason_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status: Mapped[CreditNoteStatus] = mapped_column(
        Enum(CreditNoteStatus, name="credit_note_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=CreditNoteStatus.DRAFT,
        nullable=False,
    )

    taxable_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cgst_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    sgst_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    igst_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_amount_minor: Mapped[int] = mapped_column(
        BigInteger, nullable=False, doc="taxable + cgst + sgst + igst; the total value credited back"
    )
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True
    )
    refund_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("refunds.id"),
        nullable=True,
        doc="Set once this credit note is linked to a Refund that pays it out",
    )

    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    issued_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    gst_invoice: Mapped["Invoice | None"] = relationship(back_populates="credit_notes")  # noqa: F821
    refund: Mapped["refund | None"] = relationship(  # noqa: F821 # type: ignore
        back_populates="credit_notes", foreign_keys=[refund_id]
    )

    def __repr__(self) -> str:
        return f"<CreditNote {self.credit_note_number} {self.status} total={self.total_amount_minor}>"
