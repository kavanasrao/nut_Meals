"""WhatsApp provider factory.

No other module should import a concrete provider directly.
"""
from __future__ import annotations

from app.core.config import settings
from app.providers.base import WhatsAppProvider
from app.providers.meta_provider import MetaWhatsAppProvider
from app.providers.twilio_provider import TwilioProvider

_PROVIDER_REGISTRY: dict[str, type[WhatsAppProvider]] = {
    "twilio": TwilioProvider,
    "meta": MetaWhatsAppProvider,
}


def get_whatsapp_provider() -> WhatsAppProvider:
    """Resolve and instantiate the configured WhatsApp provider."""
    name = settings.WHATSAPP_PROVIDER.lower().strip()
    provider_class = _PROVIDER_REGISTRY.get(name)
    if provider_class is None:
        registered = list(_PROVIDER_REGISTRY.keys())
        raise ValueError(
            f"Unknown WhatsApp provider '{name}'. "
            f"Set WHATSAPP_PROVIDER to one of: {registered}"
        )
    return provider_class()
