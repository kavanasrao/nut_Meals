import pytest

from app.models.dlq import DeadLetter
from app.models.message import Message, MessageChannel, MessageStatus


async def _seed_dead_letter(db_session):
    message = Message(
        event_type="order.status_changed",
        channel=MessageChannel.EMAIL,
        recipient="bad@bad",
        body="oops",
        idempotency_key="dlq-api-test-1",
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
        recipient="bad@bad",
        payload_snapshot={"body": "oops"},
        failure_reason="invalid recipient",
        attempt_count=5,
    )
    db_session.add(dl)
    await db_session.commit()
    await db_session.refresh(dl)
    return message, dl


@pytest.mark.asyncio
async def test_list_dlq_requires_read_role(client):
    resp = await client.get("/api/v1/dlq")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_dlq_success(client, db_session, auditor_token):
    await _seed_dead_letter(db_session)
    resp = await client.get("/api/v1/dlq", headers={"Authorization": f"Bearer {auditor_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_reprocess_requires_admin_role(client, db_session, auditor_token):
    _, dl = await _seed_dead_letter(db_session)
    resp = await client.post(
        f"/api/v1/dlq/{dl.id}/reprocess",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"reset_attempts": True},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_reprocess_not_found(client, admin_token):
    resp = await client.post(
        "/api/v1/dlq/00000000-0000-0000-0000-000000000000/reprocess",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reset_attempts": True},
    )
    assert resp.status_code == 404
