import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import LedgerEntryType
from app.models.vendor import Vendor, VendorLedgerEntry
from app.schemas.vendor import (
    VendorCreate,
    VendorLedgerEntryCreate,
    VendorUpdate,
)


class VendorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_vendor(self, payload: VendorCreate) -> Vendor:
        vendor = Vendor(**payload.model_dump())
        self.db.add(vendor)
        await self.db.commit()
        await self.db.refresh(vendor)
        return vendor

    async def get_vendor(self, vendor_id: uuid.UUID) -> Vendor:
        vendor = await self.db.get(Vendor, vendor_id)
        if vendor is None or vendor.is_deleted:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Vendor not found")
        return vendor

    async def list_vendors(
        self, page: int, page_size: int, status_filter: str | None = None
    ) -> tuple[list[Vendor], int]:
        stmt = select(Vendor).where(Vendor.is_deleted.is_(False))
        count_stmt = select(func.count()).select_from(Vendor).where(
            Vendor.is_deleted.is_(False)
        )
        if status_filter:
            stmt = stmt.where(Vendor.status == status_filter)
            count_stmt = count_stmt.where(Vendor.status == status_filter)

        total = (await self.db.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(Vendor.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def update_vendor(self, vendor_id: uuid.UUID, payload: VendorUpdate) -> Vendor:
        vendor = await self.get_vendor(vendor_id)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(vendor, field, value)
        await self.db.commit()
        await self.db.refresh(vendor)
        return vendor

    async def delete_vendor(self, vendor_id: uuid.UUID) -> None:
        vendor = await self.get_vendor(vendor_id)
        vendor.is_deleted = True
        await self.db.commit()

    # --- Ledger ---

    async def get_current_balance(self, vendor_id: uuid.UUID) -> Decimal:
        stmt = (
            select(VendorLedgerEntry.balance_after)
            .where(VendorLedgerEntry.vendor_id == vendor_id)
            .order_by(VendorLedgerEntry.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        balance = result.scalar_one_or_none()
        return balance if balance is not None else Decimal("0")

    async def add_ledger_entry(
        self, vendor_id: uuid.UUID, payload: VendorLedgerEntryCreate
    ) -> VendorLedgerEntry:
        await self.get_vendor(vendor_id)  # ensures vendor exists & not deleted
        current_balance = await self.get_current_balance(vendor_id)

        if payload.entry_type == LedgerEntryType.DEBIT:
            new_balance = current_balance + payload.amount
        else:
            new_balance = current_balance - payload.amount

        entry = VendorLedgerEntry(
            vendor_id=vendor_id,
            entry_type=payload.entry_type,
            source=payload.source,
            reference_id=payload.reference_id,
            amount=payload.amount,
            balance_after=new_balance,
            description=payload.description,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def list_ledger_entries(self, vendor_id: uuid.UUID) -> list[VendorLedgerEntry]:
        await self.get_vendor(vendor_id)
        stmt = (
            select(VendorLedgerEntry)
            .where(VendorLedgerEntry.vendor_id == vendor_id)
            .order_by(VendorLedgerEntry.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
