"""
Affiliate Commission API routes.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.affiliate_commission import (
    AffiliateCommissionCreate,
    AffiliateCommissionResponse,
    AffiliateCommissionUpdate,
)
from app.services.commission_service import CommissionService

router = APIRouter(
    prefix="/affiliate-commissions",
    tags=["Affiliate Commissions"],
)


# ==========================================================
# CREATE
# ==========================================================

@router.post(
    "",
    response_model=AffiliateCommissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_commission(
    payload: AffiliateCommissionCreate,
    db: AsyncSession = Depends(get_db),
):
    service = CommissionService(db)
    return await service.create_commission(payload)


# ==========================================================
# LIST
# ==========================================================

@router.get(
    "",
    response_model=list[AffiliateCommissionResponse],
)
async def list_commissions(
    db: AsyncSession = Depends(get_db),
):
    service = CommissionService(db)
    return await service.list_commissions()


# ==========================================================
# GET
# ==========================================================

@router.get(
    "/{commission_id}",
    response_model=AffiliateCommissionResponse,
)
async def get_commission(
    commission_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CommissionService(db)
    return await service.get_commission(commission_id)


# ==========================================================
# UPDATE
# ==========================================================

@router.put(
    "/{commission_id}",
    response_model=AffiliateCommissionResponse,
)
async def update_commission(
    commission_id: UUID,
    payload: AffiliateCommissionUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = CommissionService(db)
    return await service.update_commission(
        commission_id,
        payload,
    )

# ==========================================================
# APPROVE
# ==========================================================

@router.patch(
    "/{commission_id}/approve",
    response_model=AffiliateCommissionResponse,
)
async def approve_commission(
    commission_id: UUID,
    approved_by: str,
    db: AsyncSession = Depends(get_db),
):
    service = CommissionService(db)
    return await service.approve_commission(
        commission_id,
        approved_by,
    )


# ==========================================================
# REJECT
# ==========================================================

@router.patch(
    "/{commission_id}/reject",
    response_model=AffiliateCommissionResponse,
)
async def reject_commission(
    commission_id: UUID,
    remarks: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    service = CommissionService(db)
    return await service.reject_commission(
        commission_id,
        remarks,
    )


# ==========================================================
# MARK AS PAID
# ==========================================================

@router.patch(
    "/{commission_id}/paid",
    response_model=AffiliateCommissionResponse,
)
async def mark_as_paid(
    commission_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CommissionService(db)
    return await service.mark_as_paid(
        commission_id
    )


# ==========================================================
# ASSIGN PAYOUT
# ==========================================================

@router.patch(
    "/{commission_id}/assign-payout/{payout_id}",
    response_model=AffiliateCommissionResponse,
)
async def assign_payout(
    commission_id: UUID,
    payout_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CommissionService(db)
    return await service.assign_payout(
        commission_id,
        payout_id,
    )

# ==========================================================
# DELETE
# ==========================================================

@router.delete(
    "/{commission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_commission(
    commission_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CommissionService(db)

    await service.delete_commission(
        commission_id
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )