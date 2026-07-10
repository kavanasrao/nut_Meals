import uuid

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class CampaignAudience(BaseModel):
    __tablename__ = "campaign_audience"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    is_sent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_delivered: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_opened: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_clicked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    campaign = relationship(
        "Campaign",
        back_populates="audience",
    )

    customer = relationship(
        "CustomerProfile",
    )
    