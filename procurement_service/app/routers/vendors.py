import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_read, require_write
from app.core.security import CurrentUser
from app.database import get_db
from app.models.base import VendorStatus
from app.schemas.vendor import (
    VendorCreate,
    VendorLedgerEntryCreate,
    VendorLedgerEntryRead,
    VendorLedgerResponse,
    VendorListResponse,
    VendorRead,
    VendorUpdate,
)
from app.services.vendor_service import VendorService

router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.post("", response_model=VendorRead, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    payload: VendorCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_write),
):
    return await VendorService(db).create_vendor(payload)


@router.get("", response_model=VendorListResponse)
async def list_vendors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: VendorStatus | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_read),
):
    items, total = await VendorService(db).list_vendors(page, page_size, status_filter)
    return VendorListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{vendor_id}", response_model=VendorRead)
async def get_vendor(
    vendor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_read),
):
    return await VendorService(db).get_vendor(vendor_id)


@router.patch("/{vendor_id}", response_model=VendorRead)
async def update_vendor(
    vendor_id: uuid.UUID,
    payload: VendorUpdate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_write),
):
    return await VendorService(db).update_vendor(vendor_id, payload)


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_write),
):
    await VendorService(db).delete_vendor(vendor_id)


@router.get("/{vendor_id}/ledger", response_model=VendorLedgerResponse)
async def get_vendor_ledger(
    vendor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_read),
):
    service = VendorService(db)
    entries = await service.list_ledger_entries(vendor_id)
    balance = await service.get_current_balance(vendor_id)
    return VendorLedgerResponse(
        vendor_id=vendor_id, current_balance=balance, entries=entries
    )


@router.post(
    "/{vendor_id}/ledger",
    response_model=VendorLedgerEntryRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_ledger_entry(
    vendor_id: uuid.UUID,
    payload: VendorLedgerEntryCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_write),
):
    """Manual ledger adjustment (e.g. write-off, opening balance correction)."""
    return await VendorService(db).add_ledger_entry(vendor_id, payload)
