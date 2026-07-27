"""
Affiliate Payout API routes.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.affiliate_payout import (
    AffiliatePayoutCreate,
    AffiliatePayoutResponse,
    AffiliatePayoutUpdate,
)
from app.services.payout_service import PayoutService

router = APIRouter(
    prefix="/affiliate-payouts",
    tags=["Affiliate Payouts"],
)


# ==========================================================
# CREATE
# ==========================================================

@router.post(
    "",
    response_model=AffiliatePayoutResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_payout(
    payload: AffiliatePayoutCreate,
    db: AsyncSession = Depends(get_db),
):
    service = PayoutService(db)
    return await service.create_payout(payload)


# ==========================================================
# LIST
# ==========================================================

@router.get(
    "",
    response_model=list[AffiliatePayoutResponse],
)
async def list_payouts(
    db: AsyncSession = Depends(get_db),
):
    service = PayoutService(db)
    return await service.list_payouts()


# ==========================================================
# GET
# ==========================================================

@router.get(
    "/{payout_id}",
    response_model=AffiliatePayoutResponse,
)
async def get_payout(
    payout_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = PayoutService(db)
    return await service.get_payout(payout_id)


# ==========================================================
# UPDATE
# ==========================================================

@router.put(
    "/{payout_id}",
    response_model=AffiliatePayoutResponse,
)
async def update_payout(
    payout_id: UUID,
    payload: AffiliatePayoutUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = PayoutService(db)
    return await service.update_payout(
        payout_id,
        payload,
    )

# ==========================================================
# APPROVE
# ==========================================================

@router.patch(
    "/{payout_id}/approve",
    response_model=AffiliatePayoutResponse,
)
async def approve_payout(
    payout_id: UUID,
    approved_by: str,
    db: AsyncSession = Depends(get_db),
):
    service = PayoutService(db)
    return await service.approve_payout(
        payout_id,
        approved_by,
    )


# ==========================================================
# MARK AS PAID
# ==========================================================

@router.patch(
    "/{payout_id}/paid",
    response_model=AffiliatePayoutResponse,
)
async def mark_as_paid(
    payout_id: UUID,
    transaction_reference: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    service = PayoutService(db)
    return await service.mark_as_paid(
        payout_id,
        transaction_reference,
    )


# ==========================================================
# MARK AS FAILED
# ==========================================================

@router.patch(
    "/{payout_id}/failed",
    response_model=AffiliatePayoutResponse,
)
async def mark_as_failed(
    payout_id: UUID,
    failure_reason: str,
    db: AsyncSession = Depends(get_db),
):
    service = PayoutService(db)
    return await service.mark_as_failed(
        payout_id,
        failure_reason,
    )

# ==========================================================
# DELETE
# ==========================================================

@router.delete(
    "/{payout_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_payout(
    payout_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = PayoutService(db)

    await service.delete_payout(
        payout_id
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )