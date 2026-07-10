import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class CustomerSegment(BaseModel):
    __tablename__ = "customer_segments"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_dynamic: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    rule_expression: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    customer = relationship(
        "CustomerProfile",
        back_populates="segments",
    )