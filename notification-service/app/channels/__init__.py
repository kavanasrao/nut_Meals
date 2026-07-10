from app.channels.base import ChannelSendError
from app.channels.email import EmailChannel
from app.channels.sms import SMSChannel
from app.channels.whatsapp import WhatsAppChannel
from app.channels.webhook import WebhookChannel
from app.models.message import MessageChannel

CHANNEL_REGISTRY = {
    MessageChannel.EMAIL: EmailChannel(),
    MessageChannel.SMS: SMSChannel(),
    MessageChannel.WHATSAPP: WhatsAppChannel(),
    MessageChannel.WEBHOOK: WebhookChannel(),
}

__all__ = ["CHANNEL_REGISTRY", "ChannelSendError"]
