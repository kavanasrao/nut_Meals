"""
Unit tests for Celery task business logic. We exercise the async helper
functions directly (see app/workers/tasks.py) rather than the sync Celery
task wrappers, since the wrappers call asyncio.run() internally and can't
be invoked from within an already-running event loop (as pytest-asyncio
provides). The sync wrappers themselves are trivial pass-throughs.
"""
from unittest.mock import patch

import pytest

from app.models.dlq import DeadLetter
from app.models.message import Message, MessageChannel, MessageStatus


class _CtxManager:
    """Minimal async context manager standing in for AsyncSessionLocal()."""

    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *args):
        return False


@pytest.mark.asyncio
async def test_relay_outbox_async_enqueues_and_marks_published(db_session):
    from app.schemas.message import MessageCreate
    from app.services.outbox_service import enqueue_message
    from app.workers.tasks import _relay_outbox_async

    await enqueue_message(
        db_session,
        MessageCreate(
            event_type="order.status_changed",
            channel=MessageChannel.EMAIL,
            recipient="a@b.com",
            body="hi",
            idempotency_key="worker-test-1",
        ),
    )

    enqueued_ids = []
    with patch("app.workers.tasks.AsyncSessionLocal", return_value=_CtxManager(db_session)):
        count = await _relay_outbox_async(enqueued_ids.append)

    assert count == 1
    assert len(enqueued_ids) == 1


@pytest.mark.asyncio
async def test_retry_failed_messages_async_finds_due_messages(db_session):
    from datetime import datetime, timedelta, timezone
    from app.workers.tasks import _retry_failed_messages_async

    due_message = Message(
        event_type="order.status_changed",
        channel=MessageChannel.EMAIL,
        recipient="a@b.com",
        body="hi",
        idempotency_key="worker-retry-due",
        status=MessageStatus.FAILED,
        next_retry_at=datetime.now(timezone.utc) - timedelta(seconds=5),
        attempt_count=1,
    )
    not_due_message = Message(
        event_type="order.status_changed",
        channel=MessageChannel.EMAIL,
        recipient="b@b.com",
        body="hi",
        idempotency_key="worker-retry-not-due",
        status=MessageStatus.FAILED,
        next_retry_at=datetime.now(timezone.utc) + timedelta(hours=1),
        attempt_count=1,
    )
    db_session.add_all([due_message, not_due_message])
    await db_session.commit()

    enqueued_ids = []
    with patch("app.workers.tasks.AsyncSessionLocal", return_value=_CtxManager(db_session)):
        count = await _retry_failed_messages_async(enqueued_ids.append)

    assert count == 1
    assert str(due_message.id) in enqueued_ids


@pytest.mark.asyncio
async def test_process_dlq_async_reprocesses_message(db_session):
    from app.workers.tasks import _process_dlq_async

    message = Message(
        event_type="order.status_changed",
        channel=MessageChannel.EMAIL,
        recipient="a@b.com",
        body="hi",
        idempotency_key="worker-test-2",
        status=MessageStatus.DEAD,
        attempt_count=5,
        max_retries=5,
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    dl = DeadLetter(
        message_id=message.id,
        channel="email",
        recipient="a@b.com",
        payload_snapshot={},
        failure_reason="boom",
        attempt_count=5,
    )
    db_session.add(dl)
    await db_session.commit()
    await db_session.refresh(dl)

    enqueued_ids = []
    with patch("app.workers.tasks.AsyncSessionLocal", return_value=_CtxManager(db_session)):
        result = await _process_dlq_async(str(dl.id), True, enqueued_ids.append)

    assert result is True
    assert enqueued_ids == [str(message.id)]
    await db_session.refresh(message)
    assert message.status == MessageStatus.PENDING
    assert message.attempt_count == 0


@pytest.mark.asyncio
async def test_process_dlq_async_returns_false_when_already_reprocessed(db_session):
    from app.workers.tasks import _process_dlq_async

    message = Message(
        event_type="order.status_changed",
        channel=MessageChannel.EMAIL,
        recipient="a@b.com",
        body="hi",
        idempotency_key="worker-test-3",
        status=MessageStatus.DEAD,
        attempt_count=5,
        max_retries=5,
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    dl = DeadLetter(
        message_id=message.id,
        channel="email",
        recipient="a@b.com",
        payload_snapshot={},
        failure_reason="boom",
        attempt_count=5,
        reprocessed=True,
    )
    db_session.add(dl)
    await db_session.commit()
    await db_session.refresh(dl)

    with patch("app.workers.tasks.AsyncSessionLocal", return_value=_CtxManager(db_session)):
        result = await _process_dlq_async(str(dl.id), True, lambda mid: None)

    assert result is False


@pytest.mark.asyncio
async def test_dispatch_message_async_calls_dispatch_fn(db_session):
    from unittest.mock import AsyncMock
    from app.workers.tasks import _dispatch_message_async

    message = Message(
        event_type="order.status_changed",
        channel=MessageChannel.EMAIL,
        recipient="a@b.com",
        body="hi",
        idempotency_key="worker-test-4",
        status=MessageStatus.PENDING,
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    mock_dispatch = AsyncMock()
    with patch("app.workers.tasks.AsyncSessionLocal", return_value=_CtxManager(db_session)):
        await _dispatch_message_async(str(message.id), dispatch_fn=mock_dispatch)

    mock_dispatch.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_message_async_handles_missing_message(db_session):
    from unittest.mock import AsyncMock
    from app.workers.tasks import _dispatch_message_async

    mock_dispatch = AsyncMock()
    with patch("app.workers.tasks.AsyncSessionLocal", return_value=_CtxManager(db_session)):
        await _dispatch_message_async("00000000-0000-0000-0000-000000000000", dispatch_fn=mock_dispatch)

    mock_dispatch.assert_not_awaited()
