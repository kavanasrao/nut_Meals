from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.refund import RefundStatus
from app.schemas.refund import (
    RefundCreate,
    RefundUpdate,
    RefundResponse,
)
from app.services.refund_service import RefundService

router = APIRouter(
    prefix="/refunds",
    tags=["Refunds"],
)


def get_refund_service(
    db: AsyncSession = Depends(get_db),
) -> RefundService:
    return RefundService(db)


# =====================================================
# CREATE
# =====================================================

@router.post(
    "/",
    response_model=RefundResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_refund(
    payload: RefundCreate,
    service: RefundService = Depends(get_refund_service),
):
    return await service.create_refund(payload)


# =====================================================
# GET
# =====================================================

@router.get(
    "/",
    response_model=list[RefundResponse],
)
async def list_refunds(
    service: RefundService = Depends(get_refund_service),
):
    return await service.list_refunds()


@router.get(
    "/{refund_id}",
    response_model=RefundResponse,
)
async def get_refund(
    refund_id: UUID,
    service: RefundService = Depends(get_refund_service),
):
    return await service.get_refund(refund_id)


@router.get(
    "/gateway/{gateway_refund_id}",
    response_model=RefundResponse,
)
async def get_by_gateway_id(
    gateway_refund_id: str,
    service: RefundService = Depends(get_refund_service),
):
    return await service.get_refund_by_gateway_id(
        gateway_refund_id
    )


@router.get(
    "/status/{status}",
    response_model=list[RefundResponse],
)
async def list_by_status(
    status: RefundStatus,
    service: RefundService = Depends(get_refund_service),
):
    return await service.list_refunds_by_status(status)


@router.get(
    "/order/{order_reference}",
    response_model=list[RefundResponse],
)
async def list_by_order(
    order_reference: str,
    service: RefundService = Depends(get_refund_service),
):
    return await service.list_refunds_by_order(
        order_reference
    )


# =====================================================
# UPDATE
# =====================================================

@router.put(
    "/{refund_id}",
    response_model=RefundResponse,
)
async def update_refund(
    refund_id: UUID,
    payload: RefundUpdate,
    service: RefundService = Depends(get_refund_service),
):
    return await service.update_refund(
        refund_id,
        payload,
    )


# =====================================================
# PROCESS
# =====================================================

@router.post(
    "/{refund_id}/process",
    response_model=RefundResponse,
)
async def process_refund(
    refund_id: UUID,
    gateway_refund_id: str,
    processed_by: str,
    service: RefundService = Depends(get_refund_service),
):
    return await service.process_refund(
        refund_id,
        gateway_refund_id,
        processed_by,
    )


@router.post(
    "/{refund_id}/fail",
    response_model=RefundResponse,
)
async def fail_refund(
    refund_id: UUID,
    reason: str,
    processed_by: str,
    service: RefundService = Depends(get_refund_service),
):
    return await service.fail_refund(
        refund_id,
        reason,
        processed_by,
    )


@router.post(
    "/{refund_id}/cancel",
    response_model=RefundResponse,
)
async def cancel_refund(
    refund_id: UUID,
    cancelled_by: str,
    reason: str | None = None,
    service: RefundService = Depends(get_refund_service),
):
    return await service.cancel_refund(
        refund_id,
        cancelled_by,
        reason,
    )