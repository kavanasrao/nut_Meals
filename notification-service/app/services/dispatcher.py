"""
Core dispatch logic shared by Celery tasks: pick a channel adapter,
attempt delivery, and route the outcome to success / retry / DLQ.
"""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels import CHANNEL_REGISTRY, ChannelSendError
from app.core.retry_policy import compute_next_retry, should_dead_letter
from app.models.dlq import DeadLetter
from app.models.message import Message, MessageStatus
from app.services.audit_service import record_audit_event


async def dispatch_message(db: AsyncSession, message: Message) -> Message:
    """
    Attempt to deliver `message` via its channel adapter. Mutates and
    persists the message's status/attempt fields. Never raises —
    failures are captured and routed to retry or DLQ.
    """
    message.status = MessageStatus.PROCESSING
    message.attempt_count += 1
    await db.commit()

    channel_adapter = CHANNEL_REGISTRY.get(message.channel)
    if channel_adapter is None:
        message.status = MessageStatus.FAILED
        message.last_error = f"No adapter registered for channel {message.channel}"
        await db.commit()
        await record_audit_event(db, message, action="failed", status="failed", detail={"reason": message.last_error})
        return message

    try:
        result = await channel_adapter.send(message)
        message.status = MessageStatus.SENT
        message.sent_at = datetime.now(timezone.utc)
        message.last_error = None
        await db.commit()
        await record_audit_event(db, message, action="sent", status="sent", detail=result)
        return message

    except ChannelSendError as exc:
        message.last_error = str(exc)

        if not exc.retryable or should_dead_letter(message.attempt_count, message.max_retries):
            await _move_to_dlq(db, message, reason=str(exc))
        else:
            message.status = MessageStatus.FAILED
            message.next_retry_at = compute_next_retry(message.attempt_count)
            await db.commit()
            await record_audit_event(
                db, message, action="retry_scheduled", status="failed",
                detail={"error": str(exc), "next_retry_at": message.next_retry_at.isoformat()},
            )
        return message


async def _move_to_dlq(db: AsyncSession, message: Message, reason: str) -> None:
    message.status = MessageStatus.DEAD
    dead_letter = DeadLetter(
        message_id=message.id,
        channel=message.channel.value,
        recipient=message.recipient,
        payload_snapshot={
            "subject": message.subject,
            "body": message.body,
            "payload": message.payload,
        },
        failure_reason=reason,
        attempt_count=message.attempt_count,
    )
    db.add(dead_letter)
    await db.commit()
    await record_audit_event(db, message, action="dead_lettered", status="dead", detail={"reason": reason})
