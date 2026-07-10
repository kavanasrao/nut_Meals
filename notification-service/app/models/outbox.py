import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Integer, JSON, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class OutboxStatus(str, enum.Enum):
    NEW = "new"
    PUBLISHED = "published"
    FAILED = "failed"


class OutboxEvent(Base):
    """
    Transactional Outbox: the domain-event write and the "intent to notify"
    write happen in ONE local DB transaction. A relay (poller or CDC) later
    reads NEW rows and enqueues Celery dispatch tasks, guaranteeing
    at-least-once delivery even if the process crashes right after commit.
    """
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    status: Mapped[OutboxStatus] = mapped_column(Enum(OutboxStatus), default=OutboxStatus.NEW, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
