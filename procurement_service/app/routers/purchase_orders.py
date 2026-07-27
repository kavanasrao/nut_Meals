import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_approver, require_read, require_write
from app.core.security import CurrentUser
from app.database import get_db
from app.models.base import PurchaseOrderStatus
from app.schemas.purchase_order import (
    PurchaseOrderApproval,
    PurchaseOrderCreate,
    PurchaseOrderListResponse,
    PurchaseOrderRead,
    PurchaseOrderUpdate,
)
from app.services.po_service import PurchaseOrderService

router = APIRouter(prefix="/purchase-orders", tags=["Purchase Orders"])


@router.post("", response_model=PurchaseOrderRead, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    payload: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_write),
):
    return await PurchaseOrderService(db).create_po(payload, created_by=user.id)


@router.get("", response_model=PurchaseOrderListResponse)
async def list_purchase_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vendor_id: uuid.UUID | None = None,
    status_filter: PurchaseOrderStatus | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_read),
):
    items, total = await PurchaseOrderService(db).list_pos(
        page, page_size, vendor_id, status_filter
    )
    return PurchaseOrderListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{po_id}", response_model=PurchaseOrderRead)
async def get_purchase_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_read),
):
    return await PurchaseOrderService(db).get_po(po_id)


@router.patch("/{po_id}", response_model=PurchaseOrderRead)
async def update_purchase_order(
    po_id: uuid.UUID,
    payload: PurchaseOrderUpdate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_write),
):
    return await PurchaseOrderService(db).update_po(po_id, payload)


@router.post("/{po_id}/approval", response_model=PurchaseOrderRead)
async def approve_or_reject_purchase_order(
    po_id: uuid.UUID,
    payload: PurchaseOrderApproval,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_approver),
):
    return await PurchaseOrderService(db).approve_or_reject_po(
        po_id, payload, approver_id=user.id
    )


@router.post("/{po_id}/cancel", response_model=PurchaseOrderRead)
async def cancel_purchase_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_write),
):
    return await PurchaseOrderService(db).cancel_po(po_id)
