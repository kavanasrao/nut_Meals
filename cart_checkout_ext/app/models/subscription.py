"""ORM model for recurring meal subscriptions."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SubscriptionFrequency(str, enum.Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    EXPIRED = "expired"


class Subscription(Base):
    """
    A recurring meal-plan subscription for a customer. Billing is delegated
    to the Payments service via `payment_method_token`; this record tracks
    lifecycle state and scheduling only — it does not store raw card data.
    """
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    plan_id: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    frequency: Mapped[SubscriptionFrequency] = mapped_column(
        Enum(SubscriptionFrequency, name="subscription_frequency"), nullable=False
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
        index=True,
    )

    price_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    payment_method_token: Mapped[str] = mapped_column(String(255), nullable=False)
    shipping_address_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    next_renewal_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_renewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_renewal_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    renewal_notice_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
