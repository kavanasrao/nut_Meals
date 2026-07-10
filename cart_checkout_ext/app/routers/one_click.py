"""API routes for one-click login checkout: token issuance and fetching
saved addresses/payment methods, plus a token-gated checkout endpoint."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.one_click import (
    OneClickCheckoutRequest,
    OneClickCheckoutResponse,
    OneClickTokenResponse,
    SavedAddressResponse,
    SavedPaymentMethodResponse,
)
from app.security.audit import log_audit_event
from app.security.auth import Principal
from app.security.rbac import require_customer
from app.services.one_click_service import OneClickService

router = APIRouter(prefix="/api/v1/one-click", tags=["one-click-checkout"])


@router.post("/token", response_model=OneClickTokenResponse)
async def issue_one_click_token(
    principal: Principal = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    Issue a short-lived, single-use token for the currently authenticated
    customer. The client stores this token and presents it at checkout
    time instead of requiring another full login.
    """
    service = OneClickService(db)
    token, expires_at = await service.issue_token(uuid.UUID(principal.customer_id))
    return OneClickTokenResponse(token=token, expires_at=expires_at)


@router.get("/addresses", response_model=list[SavedAddressResponse])
async def list_saved_addresses(
    principal: Principal = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Fetch the customer's saved shipping addresses for checkout autofill."""
    service = OneClickService(db)
    return await service.list_saved_addresses(uuid.UUID(principal.customer_id))


@router.get("/payment-methods", response_model=list[SavedPaymentMethodResponse])
async def list_saved_payment_methods(
    principal: Principal = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Fetch tokenized references to the customer's saved payment methods."""
    service = OneClickService(db)
    return await service.list_saved_payment_methods(uuid.UUID(principal.customer_id))


@router.post("/checkout", response_model=OneClickCheckoutResponse)
async def one_click_checkout(
    payload: OneClickCheckoutRequest,
    principal: Principal = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    Complete checkout using a previously issued one-click token plus a
    saved address and payment method. The token is consumed (single-use)
    as part of this call.
    """
    service = OneClickService(db)
    customer_id = uuid.UUID(principal.customer_id)

    await service.consume_token(customer_id, payload.token)
    address = await service.get_saved_address(customer_id, payload.saved_address_id)
    payment_method = await service.get_saved_payment_method(customer_id, payload.saved_payment_method_id)

    # In production this would call the core Checkout service to finalize
    # the order using `payload.order_id`, the resolved address, and the
    # resolved payment method token. That call is out of scope here.
    log_audit_event(
        actor_id=str(customer_id),
        action="one_click.checkout",
        resource=f"order:{payload.order_id}",
    )

    return OneClickCheckoutResponse(
        order_id=payload.order_id,
        status="confirmed",
        address=address,
        payment_method=payment_method,
    )
