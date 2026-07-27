from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.gst import (
    GSTRateCreate,
    GSTRateUpdate,
    GSTRateResponse,
)
from app.services.gst_service import GSTService

from app.schemas.gst import (
    GSTInvoiceCreate,
    GSTInvoiceResponse,
)
from app.models.gst import GSTInvoiceStatus


router = APIRouter(
    prefix="/gst",
    tags=["GST"],
)


def get_gst_service(
    db: AsyncSession = Depends(get_db),
) -> GSTService:
    return GSTService(db)


# ==========================================================
# GST RATE CRUD
# ==========================================================

@router.post(
    "/rates",
    response_model=GSTRateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_rate(
    payload: GSTRateCreate,
    service: GSTService = Depends(get_gst_service),
):
    return await service.create_rate(payload)


@router.get(
    "/rates",
    response_model=list[GSTRateResponse],
)
async def list_rates(
    service: GSTService = Depends(get_gst_service),
):
    return await service.list_rates()


@router.get(
    "/rates/{rate_id}",
    response_model=GSTRateResponse,
)
async def get_rate(
    rate_id: UUID,
    service: GSTService = Depends(get_gst_service),
):
    return await service.get_rate(rate_id)


@router.put(
    "/rates/{rate_id}",
    response_model=GSTRateResponse,
)
async def update_rate(
    rate_id: UUID,
    payload: GSTRateUpdate,
    service: GSTService = Depends(get_gst_service),
):
    return await service.update_rate(
        rate_id,
        payload,
    )


@router.delete(
    "/rates/{rate_id}",
)
async def delete_rate(
    rate_id: UUID,
    service: GSTService = Depends(get_gst_service),
):
    return await service.delete_rate(rate_id)



# ==========================================================
# GST INVOICES
# ==========================================================

@router.post(
    "/invoices",
    response_model=GSTInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invoice(
    payload: GSTInvoiceCreate,
    service: GSTService = Depends(get_gst_service),
):
    return await service.create_invoice(payload)


@router.post(
    "/invoices/{invoice_id}/post",
    response_model=GSTInvoiceResponse,
)
async def post_invoice(
    invoice_id: UUID,
    posted_by: str,
    service: GSTService = Depends(get_gst_service),
):
    return await service.post_invoice(
        invoice_id,
        posted_by,
    )


@router.get(
    "/invoices",
    response_model=list[GSTInvoiceResponse],
)
async def list_invoices(
    status: GSTInvoiceStatus | None = Query(default=None),
    service: GSTService = Depends(get_gst_service),
):
    return await service.list_invoices(status)


@router.get(
    "/invoices/{invoice_id}",
    response_model=GSTInvoiceResponse,
)
async def get_invoice(
    invoice_id: UUID,
    service: GSTService = Depends(get_gst_service),
):
    return await service.get_invoice(invoice_id)


@router.get(
    "/invoices/number/{invoice_number}",
    response_model=GSTInvoiceResponse,
)
async def get_invoice_by_number(
    invoice_number: str,
    service: GSTService = Depends(get_gst_service),
):
    return await service.get_invoice_by_number(invoice_number)


@router.delete(
    "/invoices/{invoice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_invoice(
    invoice_id: UUID,
    service: GSTService = Depends(get_gst_service),
):
    await service.delete_draft_invoice(invoice_id)