"""Business logic for one-click login checkout: token issuance/validation
and fetching a customer's saved addresses/payment methods."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.one_click import OneClickToken, SavedAddress, SavedPaymentMethod
from app.security.audit import log_audit_event

settings = get_settings()


def _hash_token(raw_token: str) -> str:
    """Store only a hash of the token server-side; the raw value is only
    ever seen once, at issuance time, by the client."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class OneClickService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def issue_token(self, customer_id: uuid.UUID) -> tuple[str, datetime]:
        raw_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ONE_CLICK_TOKEN_EXPIRE_MINUTES
        )
        token_row = OneClickToken(
            customer_id=customer_id,
            token_hash=_hash_token(raw_token),
            expires_at=expires_at,
        )
        self.db.add(token_row)
        await self.db.commit()

        log_audit_event(
            actor_id=str(customer_id),
            action="one_click_token.issue",
            resource="one_click_token",
        )
        return raw_token, expires_at

    async def consume_token(self, customer_id: uuid.UUID, raw_token: str) -> None:
        token_hash = _hash_token(raw_token)
        result = await self.db.execute(
            select(OneClickToken).where(OneClickToken.token_hash == token_hash)
        )
        token_row = result.scalar_one_or_none()

        if token_row is None or str(token_row.customer_id) != str(customer_id):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid one-click token")
        if token_row.used:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token already used")
        if token_row.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

        token_row.used = True
        token_row.used_at = datetime.now(timezone.utc)
        await self.db.commit()

        log_audit_event(
            actor_id=str(customer_id),
            action="one_click_token.consume",
            resource="one_click_token",
        )

    async def get_saved_address(self, customer_id: uuid.UUID, address_id: uuid.UUID) -> SavedAddress:
        result = await self.db.execute(select(SavedAddress).where(SavedAddress.id == address_id))
        address = result.scalar_one_or_none()
        if address is None or str(address.customer_id) != str(customer_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
        return address

    async def get_saved_payment_method(
        self, customer_id: uuid.UUID, payment_method_id: uuid.UUID
    ) -> SavedPaymentMethod:
        result = await self.db.execute(
            select(SavedPaymentMethod).where(SavedPaymentMethod.id == payment_method_id)
        )
        payment_method = result.scalar_one_or_none()
        if payment_method is None or str(payment_method.customer_id) != str(customer_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment method not found")
        return payment_method

    async def list_saved_addresses(self, customer_id: uuid.UUID) -> list[SavedAddress]:
        result = await self.db.execute(select(SavedAddress).where(SavedAddress.customer_id == customer_id))
        return list(result.scalars().all())

    async def list_saved_payment_methods(self, customer_id: uuid.UUID) -> list[SavedPaymentMethod]:
        result = await self.db.execute(
            select(SavedPaymentMethod).where(SavedPaymentMethod.customer_id == customer_id)
        )
        return list(result.scalars().all())
