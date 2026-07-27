"""
API routes for Stock Reservation Management.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.stock_reservation import (
    StockReservationCreate,
    StockReservationOut,
)
from app.services.stock_reservation_service import (
    StockReservationService,
)

router = APIRouter(
    prefix="/stock-reservations",
    tags=["Stock Reservations"],
)


# ==========================================================
# CREATE
# ==========================================================

@router.post(
    "",
    response_model=StockReservationOut,
)
async def reserve_stock(
    data: StockReservationCreate,
    db: AsyncSession = Depends(get_db),
):

    service = StockReservationService(db)

    return await service.reserve_stock(data)


# ==========================================================
# GET
# ==========================================================

@router.get(
    "/{reservation_id}",
    response_model=StockReservationOut,
)
async def get_reservation(
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = StockReservationService(db)

    reservation = await service.get(reservation_id)

    if reservation is None:
        raise HTTPException(
            status_code=404,
            detail="Reservation not found.",
        )

    return reservation


# ==========================================================
# LIST
# ==========================================================

@router.get(
    "",
    response_model=list[StockReservationOut],
)
async def list_reservations(
    db: AsyncSession = Depends(get_db),
):

    service = StockReservationService(db)

    return await service.list()


# ==========================================================
# RELEASE
# ==========================================================

@router.patch(
    "/{reservation_id}/release",
    response_model=StockReservationOut,
)
async def release_reservation(
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = StockReservationService(db)

    reservation = await service.get(reservation_id)

    if reservation is None:
        raise HTTPException(
            status_code=404,
            detail="Reservation not found.",
        )

    return await service.release_reservation(
        reservation
    )


# ==========================================================
# FULFILL
# ==========================================================

@router.patch(
    "/{reservation_id}/fulfill",
    response_model=StockReservationOut,
)
async def fulfill_reservation(
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = StockReservationService(db)

    reservation = await service.get(reservation_id)

    if reservation is None:
        raise HTTPException(
            status_code=404,
            detail="Reservation not found.",
        )

    return await service.fulfill_reservation(
        reservation
    )


# ==========================================================
# CANCEL
# ==========================================================

@router.patch(
    "/{reservation_id}/cancel",
    response_model=StockReservationOut,
)
async def cancel_reservation(
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = StockReservationService(db)

    reservation = await service.get(reservation_id)

    if reservation is None:
        raise HTTPException(
            status_code=404,
            detail="Reservation not found.",
        )

    return await service.cancel_reservation(
        reservation
    )