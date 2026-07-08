"""Dashboard aggregation service.

Fans out to all downstream services in parallel to collect stats,
then assembles the DashboardStats response.

Falls back to zero/unknown for any service that is unavailable so the
dashboard never returns an error just because one service is down.
"""
from __future__ import annotations

import asyncio
import logging
from decimal import Decimal

from app.integrations.delivery_client import DeliveryServiceClient
from app.integrations.notification_client import NotificationServiceClient
from app.integrations.order_client import OrderServiceClient
from app.integrations.payment_client import PaymentServiceClient
from app.integrations.user_client import UserServiceClient
from app.schemas.schemas import DashboardStats

logger = logging.getLogger(__name__)


async def _safe(coro, default):
    """Await a coroutine; return `default` on any exception."""
    try:
        return await coro
    except Exception as exc:
        logger.warning("Dashboard stat failed: %s", exc)
        return default


class DashboardService:
    async def get_stats(self) -> DashboardStats:
        user_client = UserServiceClient()
        order_client = OrderServiceClient()
        payment_client = PaymentServiceClient()
        delivery_client = DeliveryServiceClient()
        notification_client = NotificationServiceClient()

        # Fan out all requests concurrently
        (
            total_users,
            order_stats,
            payment_stats,
            active_deliveries,
            payment_provider,
            wa_provider,
        ) = await asyncio.gather(
            _safe(user_client.get_user_count(), 0),
            _safe(order_client.get_order_stats(), {}),
            _safe(payment_client.get_payment_stats(), {}),
            _safe(delivery_client.get_active_deliveries_count(), 0),
            _safe(payment_client.get_current_provider(), "unknown"),
            _safe(notification_client.get_current_provider(), "unknown"),
        )

        return DashboardStats(
            total_users=int(total_users),
            total_orders=int((order_stats or {}).get("total", 0)),
            total_revenue=Decimal(str((payment_stats or {}).get("total_revenue", "0"))),
            orders_today=int((order_stats or {}).get("today", 0)),
            revenue_today=Decimal(str((payment_stats or {}).get("today_revenue", "0"))),
            active_deliveries=int(active_deliveries),
            payment_provider=str(payment_provider),
            whatsapp_provider=str(wa_provider),
        )
