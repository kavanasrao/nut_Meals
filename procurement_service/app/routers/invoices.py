import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_read, require_write
from app.core.security import CurrentUser
from app.database import get_db
from app.models.base import InvoiceStatus
from app.schemas.invoice import (
    PurchaseInvoiceCreate,
    PurchaseInvoiceListResponse,
    PurchaseInvoiceRead,
    PurchaseInvoiceStatusUpdate,
)
from app.services.invoice_service import InvoiceService

router = APIRouter(prefix="/invoices", tags=["Purchase Invoices"])


@router.post("", response_model=PurchaseInvoiceRead, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: PurchaseInvoiceCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_write),
):
    return await InvoiceService(db).create_invoice(payload)


@router.get("", response_model=PurchaseInvoiceListResponse)
async def list_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vendor_id: uuid.UUID | None = None,
    status_filter: InvoiceStatus | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_read),
):
    items, total = await InvoiceService(db).list_invoices(
        page, page_size, vendor_id, status_filter
    )
    return PurchaseInvoiceListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{invoice_id}", response_model=PurchaseInvoiceRead)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_read),
):
    return await InvoiceService(db).get_invoice(invoice_id)


@router.patch("/{invoice_id}/status", response_model=PurchaseInvoiceRead)
async def update_invoice_status(
    invoice_id: uuid.UUID,
    payload: PurchaseInvoiceStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_write),
):
    return await InvoiceService(db).update_status(invoice_id, payload)


@router.post("/{invoice_id}/match", response_model=PurchaseInvoiceRead)
async def trigger_three_way_match(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_write),
):
    """Manually trigger PO/GRN/Invoice 3-way matching (also runs automatically via Celery)."""
    return await InvoiceService(db).match_against_grn(invoice_id)
