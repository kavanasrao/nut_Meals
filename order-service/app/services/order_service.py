"""Order Service — business logic layer.

Responsibilities:
  - Validate + persist orders
  - Calculate totals (subtotal, tax, delivery charge)
  - Publish ORDER_CREATED event to Redis
"""
from __future__ import annotations

import uuid
import logging
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.events import EventType
from app.events.publisher import EventPublisher
from app.models.order import Order, OrderItem, OrderStatus
from app.schemas.order import OrderCreate, OrderStatusUpdate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (move to config/DB if they become dynamic)
# ---------------------------------------------------------------------------
GST_RATE = Decimal("0.05")          # 5% GST on food
DELIVERY_CHARGE = Decimal("49.00")  # flat ₹49 delivery fee
FREE_DELIVERY_THRESHOLD = Decimal("499.00")


class OrderService:
    """All order-related business operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_order(self, data: OrderCreate) -> Order:
        """
        1. Calculate financials.
        2. Persist Order + OrderItems in a single transaction.
        3. Publish ORDER_CREATED event (best-effort; does not roll back on failure).
        """
        order_id = uuid.uuid4()
        subtotal = self._calculate_subtotal(data)
        tax = (subtotal * GST_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        delivery = Decimal("0") if subtotal >= FREE_DELIVERY_THRESHOLD else DELIVERY_CHARGE
        total = subtotal + tax + delivery

        order = Order(
            id=order_id,
            user_id=data.user_id,
            status=OrderStatus.PENDING,
            delivery_type=data.delivery_type,
            delivery_address=data.delivery_address.model_dump() if data.delivery_address else None,
            special_instructions=data.special_instructions,
            subtotal=subtotal,
            tax_amount=tax,
            delivery_charge=delivery,
            discount_amount=Decimal("0"),
            total_amount=total,
        )
        self.db.add(order)

        # Add items
        for item_in in data.items:
            line_total = (item_in.unit_price * item_in.quantity).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            self.db.add(
                OrderItem(
                    id=uuid.uuid4(),
                    order_id=order_id,
                    meal_id=item_in.meal_id,
                    meal_name=item_in.meal_name,
                    quantity=item_in.quantity,
                    unit_price=item_in.unit_price,
                    line_total=line_total,
                )
            )

        await self.db.commit()
        await self.db.refresh(order)
        logger.info("Order %s created for user %s", order_id, data.user_id)

        # Publish event — failures here are logged, not raised, so the HTTP
        # response is still 201.  A separate outbox pattern can be added later.
        await self._publish_order_created(order)

        return order

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_order(self, order_id: str) -> Order | None:
        try:
            oid = uuid.UUID(order_id)
        except ValueError:
            return None
        result = await self.db.execute(select(Order).where(Order.id == oid))
        return result.scalar_one_or_none()

    async def list_orders_for_user(self, user_id: str) -> list[Order]:
        result = await self.db.execute(
            select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_status(self, order_id: str, update: OrderStatusUpdate) -> Order | None:
        order = await self.get_order(order_id)
        if not order:
            return None
        order.status = update.status
        await self.db.commit()
        await self.db.refresh(order)
        logger.info("Order %s status → %s", order_id, update.status)
        return order

    async def cancel_order(self, order_id: str) -> Order | None:
        return await self.update_status(
            order_id, OrderStatusUpdate(status=OrderStatus.CANCELLED)
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_subtotal(data: OrderCreate) -> Decimal:
        total = Decimal("0")
        for item in data.items:
            total += (item.unit_price * item.quantity).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        return total

    async def _publish_order_created(self, order: Order) -> None:
        try:
            await EventPublisher.publish(
                EventType.ORDER_CREATED,
                {
                    "order_id": str(order.id),
                    "user_id": order.user_id,
                    "total_amount": str(order.total_amount),
                    "subtotal": str(order.subtotal),
                    "tax_amount": str(order.tax_amount),
                    "delivery_charge": str(order.delivery_charge),
                    "delivery_type": order.delivery_type,
                    "delivery_address": order.delivery_address,
                    "items": [
                        {
                            "meal_id": i.meal_id,
                            "meal_name": i.meal_name,
                            "quantity": i.quantity,
                            "unit_price": str(i.unit_price),
                        }
                        for i in order.items
                    ],
                },
            )
        except Exception as exc:
            logger.error("Could not publish ORDER_CREATED for %s: %s", order.id, exc)
