"""
Affiliate API routes.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.affiliate import (
    AffiliateCreate,
    AffiliateResponse,
    AffiliateUpdate,
)
from app.services.affiliate_service import AffiliateService

router = APIRouter(
    prefix="/affiliates",
    tags=["Affiliates"],
)


# ==========================================================
# CREATE
# ==========================================================

@router.post(
    "",
    response_model=AffiliateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_affiliate(
    payload: AffiliateCreate,
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db)
    return await service.create_affiliate(payload)


# ==========================================================
# LIST
# ==========================================================

@router.get(
    "",
    response_model=list[AffiliateResponse],
)
async def list_affiliates(
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db)
    return await service.list_affiliates()


# ==========================================================
# GET
# ==========================================================

@router.get(
    "/{affiliate_id}",
    response_model=AffiliateResponse,
)
async def get_affiliate(
    affiliate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db)
    return await service.get_affiliate(affiliate_id)


# ==========================================================
# GET BY CODE
# ==========================================================

@router.get(
    "/code/{affiliate_code}",
    response_model=AffiliateResponse,
)
async def get_by_code(
    affiliate_code: str,
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db)
    return await service.get_by_code(affiliate_code)


# ==========================================================
# UPDATE
# ==========================================================

@router.put(
    "/{affiliate_id}",
    response_model=AffiliateResponse,
)
async def update_affiliate(
    affiliate_id: UUID,
    payload: AffiliateUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db)
    return await service.update_affiliate(
        affiliate_id,
        payload,
    )

# ==========================================================
# ACTIVATE
# ==========================================================

@router.patch(
    "/{affiliate_id}/activate",
    response_model=AffiliateResponse,
)
async def activate_affiliate(
    affiliate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db)
    return await service.activate_affiliate(
        affiliate_id
    )


# ==========================================================
# VERIFY
# ==========================================================

@router.patch(
    "/{affiliate_id}/verify",
    response_model=AffiliateResponse,
)
async def verify_affiliate(
    affiliate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db)
    return await service.verify_affiliate(
        affiliate_id
    )


# ==========================================================
# SUSPEND
# ==========================================================

@router.patch(
    "/{affiliate_id}/suspend",
    response_model=AffiliateResponse,
)
async def suspend_affiliate(
    affiliate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db)
    return await service.suspend_affiliate(
        affiliate_id
    )


# ==========================================================
# DEACTIVATE
# ==========================================================

@router.patch(
    "/{affiliate_id}/deactivate",
    response_model=AffiliateResponse,
)
async def deactivate_affiliate(
    affiliate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db)
    return await service.deactivate_affiliate(
        affiliate_id
    )


# ==========================================================
# DELETE
# ==========================================================

@router.delete(
    "/{affiliate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_affiliate(
    affiliate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db)
    await service.delete_affiliate(
        affiliate_id
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
