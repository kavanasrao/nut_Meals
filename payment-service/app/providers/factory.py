"""Payment provider factory.

Returns the correct PaymentProvider implementation based on the
PAYMENT_PROVIDER environment variable.  No other module should
import concrete provider classes directly.

Usage:
    from app.providers.factory import get_payment_provider
    provider = get_payment_provider()
    result = await provider.create_payment(data)
"""
from __future__ import annotations

from app.core.config import settings
from app.providers.base import PaymentProvider
from app.providers.juspay_provider import JuspayProvider
from app.providers.razorpay_provider import RazorpayProvider
from app.providers.stripe_provider import StripeProvider

# Registry — add new providers here
_PROVIDER_REGISTRY: dict[str, type[PaymentProvider]] = {
    "juspay": JuspayProvider,
    "stripe": StripeProvider,
    "razorpay": RazorpayProvider,
}


def get_payment_provider() -> PaymentProvider:
    """Resolve and instantiate the configured payment provider."""
    name = settings.PAYMENT_PROVIDER.lower().strip()
    provider_class = _PROVIDER_REGISTRY.get(name)
    if provider_class is None:
        registered = list(_PROVIDER_REGISTRY.keys())
        raise ValueError(
            f"Unknown payment provider '{name}'. "
            f"Set PAYMENT_PROVIDER to one of: {registered}"
        )
    return provider_class()
