"""
Payment provider factory.

Provides:
- Primary provider
- Explicit provider lookup
- Fallback provider chain
"""

from __future__ import annotations

from app.core.config import settings
from app.providers.base import PaymentProvider
from app.providers.juspay_provider import JuspayProvider
from app.providers.razorpay_provider import RazorpayProvider
from app.providers.stripe_provider import StripeProvider
from app.providers.kotak_provider import KotakProvider
# Uncomment when implemented
# from app.providers.kotak_provider import KotakProvider


_PROVIDER_REGISTRY: dict[str, type[PaymentProvider]] = {
    "juspay": JuspayProvider,
    "razorpay": RazorpayProvider,
    "stripe": StripeProvider,
    "kotak": KotakProvider,
}


_FALLBACKS: dict[str, list[str]] = {
    "juspay": ["razorpay"],
    "razorpay": [],
    "stripe": [],
    "razorpay": ["kotak"],
    "kotak": [],
}


def get_payment_provider(name: str | None = None) -> PaymentProvider:
    """
    Return configured provider.

    If name is None, uses PAYMENT_PROVIDER.
    """

    provider_name = (name or settings.PAYMENT_PROVIDER).lower().strip()

    provider_cls = _PROVIDER_REGISTRY.get(provider_name)

    if provider_cls is None:
        raise ValueError(
            f"Unsupported payment provider '{provider_name}'. "
            f"Supported providers: {list(_PROVIDER_REGISTRY.keys())}"
        )

    return provider_cls()


def get_fallback_providers() -> list[PaymentProvider]:
    """
    Return fallback providers for the configured provider.
    """

    primary = settings.PAYMENT_PROVIDER.lower().strip()

    fallbacks = _FALLBACKS.get(primary, [])

    return [
        _PROVIDER_REGISTRY[name]()
        for name in fallbacks
        if name in _PROVIDER_REGISTRY
    ]