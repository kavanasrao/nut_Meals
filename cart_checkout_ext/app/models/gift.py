"""ORM model for gift orders attached to an existing cart/order."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GiftWrapOption(str, enum.Enum):
    NONE = "none"
    STANDARD = "standard"
    PREMIUM = "premium"


class GiftOrder(Base):
    """
    Extends a base order (owned by the core Cart/Checkout service) with
    gift-specific metadata. `order_id` references the order record living in
    the core Cart/Checkout service's own database. Since this is a separate
    microservice/database, it is stored as an opaque UUID rather than a
    cross-service SQL foreign key.
    """
    __tablename__ = "gift_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    is_gift: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    gift_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recipient_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recipient_address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recipient_city: Mapped[str] = mapped_column(String(120), nullable=False)
    recipient_state: Mapped[str] = mapped_column(String(120), nullable=False)
    recipient_postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient_country: Mapped[str] = mapped_column(String(2), nullable=False, default="US")

    gift_wrap_option: Mapped[GiftWrapOption] = mapped_column(
        Enum(GiftWrapOption, name="gift_wrap_option"), default=GiftWrapOption.NONE, nullable=False
    )
    scheduled_delivery_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notify_recipient: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
