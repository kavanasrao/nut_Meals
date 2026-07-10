from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from app.channels.base import BaseChannel, ChannelSendError
from app.config import get_settings
from app.models.message import Message

settings = get_settings()


class SMSChannel(BaseChannel):
    name = "sms"

    def _client(self) -> Client:
        return Client(settings.twilio_account_sid, settings.twilio_auth_token)

    async def send(self, message: Message) -> dict:
        try:
            client = self._client()
            result = client.messages.create(
                body=message.body,
                from_=settings.twilio_from_number,
                to=message.recipient,
            )
        except TwilioRestException as exc:
            # Twilio 4xx codes for bad numbers etc. are permanent failures
            retryable = exc.status is None or exc.status >= 500
            raise ChannelSendError(f"Twilio error {exc.code}: {exc.msg}", retryable=retryable) from exc
        except Exception as exc:
            raise ChannelSendError(f"SMS send failed: {exc}", retryable=True) from exc

        return {"provider": "twilio", "sid": result.sid, "status": result.status}
