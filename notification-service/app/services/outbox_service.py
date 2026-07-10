"""
Outbox pattern write path. Business services on this microservice (or
API callers) create a Message + OutboxEvent in a single transaction so
that a crash between "decide to notify" and "actually dispatch" can
never lose a notification.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message, MessageStatus
from app.models.outbox import OutboxEvent, OutboxStatus
from app.schemas.message import MessageCreate


async def enqueue_message(db: AsyncSession, data: MessageCreate) -> Message:
    """Persist Message + OutboxEvent atomically. Idempotent on idempotency_key."""
    existing = await db.execute(select(Message).where(Message.idempotency_key == data.idempotency_key))
    existing_msg = existing.scalar_one_or_none()
    if existing_msg is not None:
        return existing_msg

    message = Message(
        id=uuid.uuid4(),
        event_type=data.event_type,
        channel=data.channel,
        recipient=data.recipient,
        subject=data.subject,
        body=data.body,
        payload=data.payload,
        correlation_id=data.correlation_id,
        priority=data.priority,
        idempotency_key=data.idempotency_key,
        max_retries=data.max_retries,
        status=MessageStatus.PENDING,
    )
    db.add(message)
    await db.flush()  # get message.id without committing yet

    outbox_event = OutboxEvent(
        id=uuid.uuid4(),
        aggregate_type="message",
        aggregate_id=str(message.id),
        event_type=data.event_type,
        event_payload=data.payload,
        status=OutboxStatus.NEW,
        message_id=message.id,
    )
    db.add(outbox_event)

    await db.commit()
    await db.refresh(message)
    return message


async def fetch_unpublished_outbox_events(db: AsyncSession, limit: int = 100) -> list[OutboxEvent]:
    result = await db.execute(
        select(OutboxEvent).where(OutboxEvent.status == OutboxStatus.NEW).order_by(OutboxEvent.created_at).limit(limit)
    )
    return list(result.scalars().all())


async def mark_outbox_published(db: AsyncSession, event: OutboxEvent) -> None:
    from datetime import datetime, timezone

    event.status = OutboxStatus.PUBLISHED
    event.published_at = datetime.now(timezone.utc)
    await db.commit()
