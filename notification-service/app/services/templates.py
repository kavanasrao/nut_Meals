"""Notification Service — WhatsApp message templates.

All user-facing message text lives here for easy maintenance.
"""
from __future__ import annotations

from typing import Any


def order_created_message(payload: dict[str, Any]) -> str:
    order_id = payload.get("order_id", "N/A")
    total = payload.get("total_amount", "0")
    items_count = len(payload.get("items", []))
    return (
        f"✅ *Order Confirmed!*\n\n"
        f"Your order #{str(order_id)[:8].upper()} has been placed successfully.\n"
        f"🛒 Items: {items_count}\n"
        f"💰 Total: ₹{total}\n\n"
        f"We'll notify you when your food is on its way. Thank you for ordering from Nutmeals! 🥗"
    )


def payment_success_message(payload: dict[str, Any]) -> str:
    order_id = payload.get("order_id", "N/A")
    amount = payload.get("amount", "0")
    return (
        f"💳 *Payment Successful!*\n\n"
        f"Payment of ₹{amount} received for order #{str(order_id)[:8].upper()}.\n\n"
        f"Your order is now being prepared. Estimated time: 30–45 mins. 🍽️"
    )


def delivery_assigned_message(payload: dict[str, Any]) -> str:
    order_id = payload.get("order_id", "N/A")
    rider = payload.get("rider_name", "our delivery partner")
    eta = payload.get("eta_minutes", "30")
    return (
        f"🛵 *Your Order is On Its Way!*\n\n"
        f"Order #{str(order_id)[:8].upper()} has been picked up by {rider}.\n"
        f"⏱️ Expected arrival: {eta} minutes.\n\n"
        f"Track your delivery in the Nutmeals app."
    )


# Map event_type → message builder function
MESSAGE_BUILDERS: dict[str, Any] = {
    "ORDER_CREATED": order_created_message,
    "PAYMENT_SUCCESS": payment_success_message,
    "DELIVERY_ASSIGNED": delivery_assigned_message,
}


def build_message(event_type: str, payload: dict[str, Any]) -> str | None:
    """Return a formatted WhatsApp message for the given event, or None if unhandled."""
    builder = MESSAGE_BUILDERS.get(event_type)
    return builder(payload) if builder else None
