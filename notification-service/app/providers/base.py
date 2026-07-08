"""Abstract WhatsApp provider interface.

To add a new WhatsApp provider:
  1. Create <name>_provider.py in this package.
  2. Subclass WhatsAppProvider and implement send_message().
  3. Register in factory.py.
  4. Set WHATSAPP_PROVIDER=<name> in .env.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass
class MessageResult:
    """Normalised result returned by all providers after sending a message."""
    provider: str
    external_message_id: str   # Provider-assigned message ID (for status tracking)
    success: bool
    error: str | None = None


class WhatsAppProvider(abc.ABC):
    """Interface all WhatsApp adapters must implement."""

    @abc.abstractmethod
    def get_name(self) -> str:
        """Return provider slug, e.g. 'twilio' or 'meta'."""

    @abc.abstractmethod
    async def send_message(self, phone: str, message: str) -> MessageResult:
        """
        Send a WhatsApp message.

        Args:
            phone: Recipient phone number in E.164 format, e.g. +919876543210
            message: Plain-text message body.

        Returns:
            MessageResult with success status and provider message ID.
        """
