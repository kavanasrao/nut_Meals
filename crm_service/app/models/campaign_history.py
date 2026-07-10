import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class CampaignHistory(BaseModel):
    __tablename__ = "campaign_history"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    event: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    channel: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    message_id: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    response_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    response_message: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    event_time: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
    )

    is_success: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    campaign = relationship(
        "Campaign",
        back_populates="history",
    )

    customer = relationship(
        "CustomerProfile",
    )