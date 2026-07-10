"""
Celery tasks. Each task opens its own short-lived async DB session
because Celery workers run in separate OS processes from the API.
"""
import asyncio
import uuid
from datetime import datetime, timezone

from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.message import Message, MessageStatus
from app.services.dispatcher import dispatch_message
from app.services.outbox_service import fetch_unpublished_outbox_events, mark_outbox_published
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


def _run_async(coro):
    return asyncio.run(coro)


# --- Async implementations (unit-testable in isolation) --------------------
# Each function below is the pure async logic; the Celery task wrappers
# further down just call asyncio.run() on these. Tests patch
# `app.workers.tasks.AsyncSessionLocal` and await these directly, avoiding
# the "asyncio.run() cannot be called from a running event loop" problem
# that comes from invoking the sync Celery task inside an async test.


async def _dispatch_message_async(message_id: str, dispatch_fn=None) -> None:
    dispatch_fn = dispatch_fn or dispatch_message
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Message).where(Message.id == uuid.UUID(message_id)))
        message = result.scalar_one_or_none()
        if message is None:
            logger.warning("dispatch_message: message %s not found", message_id)
            return
        await dispatch_fn(db, message)


async def _relay_outbox_async(enqueue_fn) -> int:
    async with AsyncSessionLocal() as db:
        events = await fetch_unpublished_outbox_events(db, limit=200)
        for event in events:
            if event.message_id:
                enqueue_fn(str(event.message_id))
            await mark_outbox_published(db, event)
        return len(events)


async def _retry_failed_messages_async(enqueue_fn) -> int:
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Message).where(
                Message.status == MessageStatus.FAILED,
                Message.next_retry_at != None,  # noqa: E711
                Message.next_retry_at <= now,
            )
        )
        due_messages = list(result.scalars().all())
        for msg in due_messages:
            enqueue_fn(str(msg.id))
        return len(due_messages)


async def _process_dlq_async(dead_letter_id: str, reset_attempts: bool, enqueue_fn) -> bool:
    from app.models.dlq import DeadLetter

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(DeadLetter).where(DeadLetter.id == uuid.UUID(dead_letter_id)))
        dl = result.scalar_one_or_none()
        if dl is None or dl.reprocessed:
            return False

        msg_result = await db.execute(select(Message).where(Message.id == dl.message_id))
        message = msg_result.scalar_one_or_none()
        if message is None:
            return False

        message.status = MessageStatus.PENDING
        if reset_attempts:
            message.attempt_count = 0
        message.next_retry_at = None
        message.last_error = None

        dl.reprocessed = True
        dl.reprocessed_at = datetime.now(timezone.utc)

        await db.commit()
        enqueue_fn(str(message.id))
        return True


# --- Celery task wrappers ----------------------------------------------------


@celery_app.task(name="app.workers.tasks.dispatch_message_task", bind=True, max_retries=0)
def dispatch_message_task(self, message_id: str):
    """Dispatch a single message by id. Retries are handled by our own
    retry engine (compute_next_retry + retry_failed_messages_task), not
    Celery's built-in retry, so that backoff state is durable in Postgres."""
    _run_async(_dispatch_message_async(message_id))


@celery_app.task(name="app.workers.tasks.relay_outbox_task")
def relay_outbox_task():
    """Poll NEW outbox rows and enqueue dispatch tasks (outbox relay)."""
    count = _run_async(_relay_outbox_async(lambda mid: dispatch_message_task.delay(mid)))
    logger.info("relay_outbox_task: published %s outbox events", count)
    return count


@celery_app.task(name="app.workers.tasks.retry_failed_messages_task")
def retry_failed_messages_task():
    """Find FAILED messages whose next_retry_at has elapsed and re-enqueue them."""
    count = _run_async(_retry_failed_messages_async(lambda mid: dispatch_message_task.delay(mid)))
    logger.info("retry_failed_messages_task: re-enqueued %s messages", count)
    return count


@celery_app.task(name="app.workers.tasks.process_dlq_task")
def process_dlq_task(dead_letter_id: str, reset_attempts: bool = True):
    """Manually triggered reprocessing of a single dead-lettered message."""
    return _run_async(
        _process_dlq_async(dead_letter_id, reset_attempts, lambda mid: dispatch_message_task.delay(mid))
    )
