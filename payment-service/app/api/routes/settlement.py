"""
Settlement REST API.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.settlement import SettlementOut
from app.services.settlement_service import SettlementService

router = APIRouter(
    prefix="/settlements",
    tags=["Settlements"],
)


@router.post(
    "/import",
    response_model=list[SettlementOut],
    status_code=status.HTTP_201_CREATED,
    summary="Import settlements from payment gateway",
)
async def import_settlements(
    db: AsyncSession = Depends(get_db),
):

    service = SettlementService(db)

    settlements = await service.import_settlements()

    return [
        SettlementOut.model_validate(item)
        for item in settlements
    ]


@router.post(
    "/{settlement_id}/reconcile",
    response_model=SettlementOut,
    summary="Reconcile settlement",
)
async def reconcile_settlement(
    settlement_id: str,
    db: AsyncSession = Depends(get_db),
):

    service = SettlementService(db)

    settlement = await service.reconcile(
        settlement_id
    )

    return SettlementOut.model_validate(
        settlement
    )


@router.get(
    "",
    response_model=list[SettlementOut],
    summary="List settlements",
)
async def list_settlements(
    db: AsyncSession = Depends(get_db),
):

    service = SettlementService(db)

    settlements = await service.list_settlements()

    return [
        SettlementOut.model_validate(item)
        for item in settlements
    ]


@router.get(
    "/{settlement_id}",
    response_model=SettlementOut,
    summary="Settlement details",
)
async def get_settlement(
    settlement_id: str,
    db: AsyncSession = Depends(get_db),
):

    service = SettlementService(db)

    settlement = await service.get_settlement(
        settlement_id
    )

    if settlement is None:
        raise HTTPException(
            status_code=404,
            detail="Settlement not found",
        )

    return SettlementOut.model_validate(
        settlement
    )