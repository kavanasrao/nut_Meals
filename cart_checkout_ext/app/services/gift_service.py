"""Business logic for gift orders."""
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gift import GiftOrder
from app.schemas.gift import GiftOrderCreate, GiftOrderUpdate
from app.security.audit import log_audit_event
from app.tasks.gift_tasks import send_gift_notification


class GiftOrderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_gift_order(self, customer_id: uuid.UUID, payload: GiftOrderCreate) -> GiftOrder:
        existing = await self.db.execute(select(GiftOrder).where(GiftOrder.order_id == payload.order_id))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A gift order already exists for this order_id.",
            )

        gift_order = GiftOrder(
            order_id=payload.order_id,
            customer_id=customer_id,
            gift_message=payload.gift_message,
            recipient_name=payload.recipient_name,
            recipient_email=payload.recipient_email,
            recipient_phone=payload.recipient_phone,
            recipient_address_line1=payload.recipient_address_line1,
            recipient_address_line2=payload.recipient_address_line2,
            recipient_city=payload.recipient_city,
            recipient_state=payload.recipient_state,
            recipient_postal_code=payload.recipient_postal_code,
            recipient_country=payload.recipient_country,
            gift_wrap_option=payload.gift_wrap_option,
            scheduled_delivery_date=payload.scheduled_delivery_date,
            notify_recipient=payload.notify_recipient,
        )
        self.db.add(gift_order)
        await self.db.commit()
        await self.db.refresh(gift_order)

        log_audit_event(
            actor_id=str(customer_id),
            action="gift_order.create",
            resource=f"gift_order:{gift_order.id}",
        )

        if gift_order.notify_recipient and gift_order.recipient_email:
            send_gift_notification.delay(str(gift_order.id))

        return gift_order

    async def get_gift_order(self, gift_order_id: uuid.UUID, customer_id: uuid.UUID) -> GiftOrder:
        result = await self.db.execute(select(GiftOrder).where(GiftOrder.id == gift_order_id))
        gift_order = result.scalar_one_or_none()
        if gift_order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift order not found")
        if str(gift_order.customer_id) != str(customer_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your gift order")
        return gift_order

    async def update_gift_order(
        self, gift_order_id: uuid.UUID, customer_id: uuid.UUID, payload: GiftOrderUpdate
    ) -> GiftOrder:
        gift_order = await self.get_gift_order(gift_order_id, customer_id)
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(gift_order, field, value)
        await self.db.commit()
        await self.db.refresh(gift_order)

        log_audit_event(
            actor_id=str(customer_id),
            action="gift_order.update",
            resource=f"gift_order:{gift_order.id}",
            metadata=update_data,
        )
        return gift_order
