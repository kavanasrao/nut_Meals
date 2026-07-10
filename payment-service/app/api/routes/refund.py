"""
Refund REST API.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.refund import RefundCreate, RefundOut
from app.services.refund_service import RefundService

router = APIRouter(
    prefix="/refunds",
    tags=["refunds"],
)


@router.post(
    "",
    response_model=RefundOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_refund(
    body: RefundCreate,
    db: AsyncSession = Depends(get_db),
) -> RefundOut:

    service = RefundService(db)

    refund = await service.create_refund(body)

    return RefundOut.model_validate(refund)


@router.get(
    "/{refund_id}",
    response_model=RefundOut,
)
async def get_refund(
    refund_id: str,
    db: AsyncSession = Depends(get_db),
) -> RefundOut:

    service = RefundService(db)

    refund = await service.get_refund(refund_id)

    if refund is None:
        raise HTTPException(
            status_code=404,
            detail="Refund not found",
        )

    return RefundOut.model_validate(refund)