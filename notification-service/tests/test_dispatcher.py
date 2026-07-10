from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.channels.base import ChannelSendError
from app.models.dlq import DeadLetter
from app.models.message import Message, MessageChannel, MessageStatus
from app.services.dispatcher import dispatch_message


async def _make_message(db_session, **overrides):
    defaults = dict(
        event_type="order.status_changed",
        channel=MessageChannel.EMAIL,
        recipient="user@example.com",
        subject="Hi",
        body="Order shipped",
        idempotency_key=f"dispatch-test-{id(overrides)}",
        max_retries=3,
        status=MessageStatus.PENDING,
    )
    defaults.update(overrides)
    message = Message(**defaults)
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)
    return message


@pytest.mark.asyncio
async def test_dispatch_success_marks_sent(db_session):
    message = await _make_message(db_session, idempotency_key="dispatch-success")

    with patch("app.services.dispatcher.CHANNEL_REGISTRY") as mock_registry:
        mock_adapter = AsyncMock()
        mock_adapter.send.return_value = {"provider": "smtp"}
        mock_registry.get.return_value = mock_adapter

        result = await dispatch_message(db_session, message)

    assert result.status == MessageStatus.SENT
    assert result.attempt_count == 1
    assert result.sent_at is not None


@pytest.mark.asyncio
async def test_dispatch_retryable_failure_schedules_retry(db_session):
    message = await _make_message(db_session, idempotency_key="dispatch-retry", max_retries=5)

    with patch("app.services.dispatcher.CHANNEL_REGISTRY") as mock_registry:
        mock_adapter = AsyncMock()
        mock_adapter.send.side_effect = ChannelSendError("temporary outage", retryable=True)
        mock_registry.get.return_value = mock_adapter

        result = await dispatch_message(db_session, message)

    assert result.status == MessageStatus.FAILED
    assert result.next_retry_at is not None
    assert result.attempt_count == 1


@pytest.mark.asyncio
async def test_dispatch_non_retryable_failure_goes_to_dlq(db_session):
    message = await _make_message(db_session, idempotency_key="dispatch-dlq", max_retries=5)

    with patch("app.services.dispatcher.CHANNEL_REGISTRY") as mock_registry:
        mock_adapter = AsyncMock()
        mock_adapter.send.side_effect = ChannelSendError("invalid recipient", retryable=False)
        mock_registry.get.return_value = mock_adapter

        result = await dispatch_message(db_session, message)

    assert result.status == MessageStatus.DEAD
    dlq_rows = (await db_session.execute(select(DeadLetter).where(DeadLetter.message_id == message.id))).scalars().all()
    assert len(dlq_rows) == 1
    assert dlq_rows[0].failure_reason == "invalid recipient"


@pytest.mark.asyncio
async def test_dispatch_exhausted_retries_goes_to_dlq(db_session):
    message = await _make_message(db_session, idempotency_key="dispatch-exhausted", max_retries=1)

    with patch("app.services.dispatcher.CHANNEL_REGISTRY") as mock_registry:
        mock_adapter = AsyncMock()
        mock_adapter.send.side_effect = ChannelSendError("still failing", retryable=True)
        mock_registry.get.return_value = mock_adapter

        result = await dispatch_message(db_session, message)

    # attempt_count becomes 1, max_retries=1 -> should_dead_letter True
    assert result.status == MessageStatus.DEAD


@pytest.mark.asyncio
async def test_dispatch_missing_adapter_marks_failed(db_session):
    message = await _make_message(db_session, idempotency_key="dispatch-no-adapter")

    with patch("app.services.dispatcher.CHANNEL_REGISTRY", {}):
        result = await dispatch_message(db_session, message)

    assert result.status == MessageStatus.FAILED
    assert "No adapter registered" in result.last_error
