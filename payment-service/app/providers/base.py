"""Abstract base class that all payment providers must implement.

To add a new provider:
  1. Create a new file in this package (e.g. razorpay_provider.py).
  2. Subclass PaymentProvider and implement all abstract methods.
  3. Register the class in factory.py.
  4. Set PAYMENT_PROVIDER=<name> in your .env.

Business logic in payment_service.py must NEVER import a concrete provider
directly — always use get_payment_provider() from factory.py.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any


@dataclass
class PaymentResult:
    """Normalised result returned by create_payment across all providers."""
    provider: str               # e.g. "juspay"
    payment_id: str             # provider-side ID / session ID
    payment_url: str            # URL the user is redirected to (or empty for server-side)
    raw: dict[str, Any]         # full provider response (stored for audit)


@dataclass
class WebhookResult:
    """Normalised result returned by verify_webhook across all providers."""
    provider: str
    order_id: str               # our internal order ID embedded in the payment
    payment_id: str             # provider-side transaction / payment ID
    status: str                 # normalised: "SUCCESS" | "FAILED" | "PENDING"
    amount: str                 # as string to avoid float issues
    raw: dict[str, Any]         # full parsed webhook payload


class PaymentProvider(abc.ABC):
    """Interface every payment provider adapter must satisfy."""

    @abc.abstractmethod
    def get_name(self) -> str:
        """Return provider slug, e.g. 'juspay'."""

    @abc.abstractmethod
    async def create_payment(self, data: dict[str, Any]) -> PaymentResult:
        """
        Initiate a payment session with the provider.

        Expected keys in `data`:
          order_id   (str) — our internal order UUID
          amount     (str) — total in INR, e.g. "499.00"
          user_id    (str)
          email      (str, optional)
          phone      (str, optional)
          return_url (str, optional)
        """

    @abc.abstractmethod
    async def verify_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> WebhookResult:
        """
        Validate the webhook signature and return a normalised WebhookResult.

        Raises ValueError if the signature is invalid or payload is malformed.
        """
