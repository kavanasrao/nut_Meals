import uuid
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import (
    AcquisitionChannel,
    CustomerSource,
    CustomerStatus,
    LoyaltyTier,
)


class CustomerProfile(BaseModel):
    __tablename__ = "customer_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    customer_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
    )

    status: Mapped[CustomerStatus] = mapped_column(
        Enum(CustomerStatus, name="customer_status"),
        default=CustomerStatus.ACTIVE,
        nullable=False,
    )

    source: Mapped[CustomerSource] = mapped_column(
        Enum(CustomerSource, name="customer_source"),
        default=CustomerSource.WEBSITE,
        nullable=False,
    )

    acquisition_channel: Mapped[AcquisitionChannel] = mapped_column(
        Enum(AcquisitionChannel, name="acquisition_channel"),
        default=AcquisitionChannel.ORGANIC,
        nullable=False,
    )

    loyalty_tier: Mapped[LoyaltyTier] = mapped_column(
        Enum(LoyaltyTier, name="loyalty_tier"),
        default=LoyaltyTier.BRONZE,
        nullable=False,
    )

    loyalty_points: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    lifetime_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        nullable=False,
    )

    addresses = relationship(
        "CustomerAddress",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    tags = relationship(
        "CustomerTag",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    segments = relationship(
        "CustomerSegment",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    timeline = relationship(
        "CustomerTimeline",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    notes = relationship(
        "CustomerNote",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    preferences = relationship(
        "CustomerPreference",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    interactions = relationship(
        "CustomerInteraction",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    tickets = relationship(
        "SupportTicket",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    loyalty_transactions = relationship(
        "LoyaltyTransaction",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    feedback = relationship(
        "CustomerFeedback",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    audits = relationship(
        "CustomerAudit",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    