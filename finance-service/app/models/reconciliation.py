"""
Settlement reconciliation models.

Payment gateway / bank settlement files (Juspay, Kotak Bank, etc.) are
ingested into `GatewaySettlement` rows, then matched against internal
order/payment records (`ReconciliationMatch`). Unmatched or mismatched
amounts are flagged for manual review via `ReconciliationException`.
"""

import enum
import uuid

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class GatewayProvider(str, enum.Enum):
    JUSPAY = "juspay"
    KOTAK_BANK = "kotak_bank"
    RAZORPAY = "razorpay"
    OTHER = "other"


class SettlementStatus(str, enum.Enum):
    IMPORTED = "imported"
    MATCHED = "matched"
    PARTIALLY_MATCHED = "partially_matched"
    MISMATCHED = "mismatched"
    UNMATCHED = "unmatched"


class ReconciliationRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ReconciliationRun(TimestampMixin, Base):
    """A single execution of the reconciliation job (usually triggered daily by Celery beat)."""

    __tablename__ = "reconciliation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[GatewayProvider] = mapped_column(
        Enum(GatewayProvider, name="gateway_provider_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    settlement_batch_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[ReconciliationRunStatus] = mapped_column(
        Enum(
            ReconciliationRunStatus,
            name="reconciliation_run_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ReconciliationRunStatus.PENDING,
        nullable=False,
    )
    total_records: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    matched_records: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    exception_records: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(100), default="celery-beat", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    settlements: Mapped[list["GatewaySettlement"]] = relationship(back_populates="run")


class GatewaySettlement(TimestampMixin, Base):
    """A single settlement line item imported from a payment gateway / bank file."""

    __tablename__ = "gateway_settlements"
    __table_args__ = (
        UniqueConstraint("provider", "provider_transaction_id", name="uq_settlement_provider_txn"),
        Index("ix_gateway_settlements_status", "status"),
        Index("ix_gateway_settlements_order_ref", "order_reference"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reconciliation_runs.id"), nullable=False)
    provider: Mapped[GatewayProvider] = mapped_column(
        Enum(GatewayProvider, name="gateway_provider_enum_2", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    provider_transaction_id: Mapped[str] = mapped_column(String(120), nullable=False)
    order_reference: Mapped[str | None] = mapped_column(
        String(100), nullable=True, doc="Order ID as reported by the gateway"
    )
    settled_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    settlement_date: Mapped[str] = mapped_column(String(10), nullable=False)
    fee_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    status: Mapped[SettlementStatus] = mapped_column(
        Enum(SettlementStatus, name="settlement_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=SettlementStatus.IMPORTED,
        nullable=False,
    )
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True, doc="Raw source row, kept for audit trail")

    run: Mapped["ReconciliationRun"] = relationship(back_populates="settlements")
    exception: Mapped["ReconciliationException | None"] = relationship(back_populates="settlement", uselist=False)


class ReconciliationException(TimestampMixin, Base):
    """Raised when a settlement cannot be cleanly matched to an internal order/payment record."""

    __tablename__ = "reconciliation_exceptions"
    __table_args__ = (Index("ix_recon_exceptions_resolved", "resolved"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    settlement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gateway_settlements.id"), unique=True, nullable=False
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    expected_amount_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    actual_amount_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    resolved: Mapped[bool] = mapped_column(default=False, nullable=False)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    settlement: Mapped["GatewaySettlement"] = relationship(back_populates="exception")
