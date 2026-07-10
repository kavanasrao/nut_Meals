import pytest

from app.models.message import MessageStatus, MessageChannel
from app.models.outbox import OutboxStatus
from app.schemas.message import MessageCreate
from app.services.outbox_service import enqueue_message, fetch_unpublished_outbox_events, mark_outbox_published


@pytest.mark.asyncio
async def test_enqueue_message_creates_message_and_outbox_row(db_session):
    data = MessageCreate(
        event_type="order.status_changed",
        channel=MessageChannel.EMAIL,
        recipient="a@b.com",
        body="hello",
        idempotency_key="outbox-test-1",
    )
    message = await enqueue_message(db_session, data)
    assert message.status == MessageStatus.PENDING

    events = await fetch_unpublished_outbox_events(db_session)
    assert len(events) == 1
    assert events[0].message_id == message.id
    assert events[0].status == OutboxStatus.NEW


@pytest.mark.asyncio
async def test_enqueue_message_is_idempotent(db_session):
    data = MessageCreate(
        event_type="order.status_changed",
        channel=MessageChannel.SMS,
        recipient="+15551112222",
        body="hi",
        idempotency_key="outbox-test-2",
    )
    m1 = await enqueue_message(db_session, data)
    m2 = await enqueue_message(db_session, data)
    assert m1.id == m2.id

    events = await fetch_unpublished_outbox_events(db_session)
    assert len(events) == 1


@pytest.mark.asyncio
async def test_mark_outbox_published(db_session):
    data = MessageCreate(
        event_type="delivery.updated",
        channel=MessageChannel.PUSH,
        recipient="token-xyz",
        body="on the way",
        idempotency_key="outbox-test-3",
    )
    await enqueue_message(db_session, data)
    events = await fetch_unpublished_outbox_events(db_session)
    await mark_outbox_published(db_session, events[0])

    remaining = await fetch_unpublished_outbox_events(db_session)
    assert len(remaining) == 0
