import aiosmtplib
from email.message import EmailMessage

from app.channels.base import BaseChannel, ChannelSendError
from app.config import get_settings
from app.models.message import Message

settings = get_settings()


class EmailChannel(BaseChannel):
    name = "email"

    async def send(self, message: Message) -> dict:
        if "@" not in message.recipient:
            raise ChannelSendError("Invalid email recipient", retryable=False)

        email = EmailMessage()
        email["From"] = settings.smtp_from
        email["To"] = message.recipient
        email["Subject"] = message.subject or "Notification"
        email.set_content(message.body)

        try:
            await aiosmtplib.send(
                email,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user or None,
                password=settings.smtp_password or None,
                start_tls=True,
            )
        except aiosmtplib.SMTPRecipientsRefused as exc:
            raise ChannelSendError(f"Recipient refused: {exc}", retryable=False) from exc
        except Exception as exc:
            raise ChannelSendError(f"SMTP send failed: {exc}", retryable=True) from exc

        return {"provider": "smtp", "to": message.recipient}
