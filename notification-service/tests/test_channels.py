from unittest.mock import AsyncMock, patch

import pytest

from app.channels.base import ChannelSendError
from app.channels.email import EmailChannel
from app.channels.webhook import WebhookChannel
from app.models.message import Message, MessageChannel, MessageStatus


def _msg(**overrides):
    defaults = dict(
        event_type="order.status_changed",
        channel=MessageChannel.EMAIL,
        recipient="user@example.com",
        subject="Hi",
        body="hello",
        idempotency_key="chan-test",
        status=MessageStatus.PENDING,
        payload={},
    )
    defaults.update(overrides)
    return Message(**defaults)


@pytest.mark.asyncio
async def test_email_channel_rejects_invalid_recipient():
    channel = EmailChannel()
    message = _msg(recipient="not-an-email")
    with pytest.raises(ChannelSendError) as exc_info:
        await channel.send(message)
    assert exc_info.value.retryable is False


@pytest.mark.asyncio
async def test_email_channel_sends_via_smtp():
    channel = EmailChannel()
    message = _msg()
    with patch("app.channels.email.aiosmtplib.send", new=AsyncMock(return_value=None)) as mock_send:
        result = await channel.send(message)
    mock_send.assert_awaited_once()
    assert result["to"] == "user@example.com"


@pytest.mark.asyncio
async def test_webhook_channel_success():
    channel = WebhookChannel()
    message = _msg(channel=MessageChannel.WEBHOOK, recipient="https://partner.example.com/hook")

    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch("app.channels.webhook.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await channel.send(message)

    assert result["status_code"] == 200


@pytest.mark.asyncio
async def test_webhook_channel_client_error_not_retryable():
    channel = WebhookChannel()
    message = _msg(channel=MessageChannel.WEBHOOK, recipient="https://partner.example.com/hook")

    mock_response = AsyncMock()
    mock_response.status_code = 400

    with patch("app.channels.webhook.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(ChannelSendError) as exc_info:
            await channel.send(message)

    assert exc_info.value.retryable is False
