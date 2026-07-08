"""Payment Service — REST API routes.

POST /api/v1/payments/create   — initiate a payment
POST /api/v1/payments/webhook  — receive provider webhook (no auth)
GET  /api/v1/payments/{order_id} — get payment status for an order
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.payment import PaymentCreate, PaymentInitResponse, PaymentOut
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])


@router.post(
    "/create",
    response_model=PaymentInitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a payment (server-side only)",
)
async def create_payment(
    body: PaymentCreate,
    db: AsyncSession = Depends(get_db),
) -> PaymentInitResponse:
    """
    Creates a payment session with the configured provider and returns
    the payment URL for the client to redirect to.

    IMPORTANT: The frontend must NEVER set order status to paid.
    Only a verified webhook from the provider triggers that transition.
    """
    svc = PaymentService(db)
    return await svc.create_payment(body)


@router.post(
    "/webhook",
    summary="Provider webhook receiver (signature-verified)",
    # No auth middleware — provider calls this directly
    status_code=status.HTTP_200_OK,
)
async def payment_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Receives raw webhook from the payment provider.
    Signature is verified inside PaymentService.handle_webhook().
    Returns HTTP 200 quickly to acknowledge receipt.
    """
    body = await request.body()
    headers = dict(request.headers)
    svc = PaymentService(db)
    try:
        return await svc.handle_webhook(headers, body)
    except ValueError as exc:
        # Signature verification failed — do NOT process
        logger.warning("Webhook rejected: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/{order_id}",
    response_model=PaymentOut,
    summary="Get payment status for an order",
)
async def get_payment(
    order_id: str,
    db: AsyncSession = Depends(get_db),
) -> PaymentOut:
    svc = PaymentService(db)
    payment = await svc.get_payment_by_order(order_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return PaymentOut.model_validate(
        {
            **{c.key: getattr(payment, c.key) for c in payment.__mapper__.columns},
            "created_at": payment.created_at.isoformat(),
            "updated_at": payment.updated_at.isoformat(),
        }
    )
