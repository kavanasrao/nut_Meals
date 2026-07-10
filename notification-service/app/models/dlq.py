import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, JSON, String, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class DeadLetter(Base):
    """
    Terminal store for messages that exhausted their retry policy.
    Ops/support can inspect via API and trigger a manual `reprocess`,
    which clones the message back into `messages` with status=PENDING.
    """
    __tablename__ = "dead_letters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False)

    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    failure_reason: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)

    reprocessed: Mapped[bool] = mapped_column(Boolean, default=False)
    reprocessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reprocessed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
