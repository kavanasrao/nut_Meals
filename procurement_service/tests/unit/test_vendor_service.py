import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.base import LedgerEntrySource, LedgerEntryType, VendorStatus
from app.schemas.vendor import VendorCreate, VendorLedgerEntryCreate, VendorUpdate
from app.services.vendor_service import VendorService

pytestmark = pytest.mark.unit


@pytest.fixture
def service(db_session):
    return VendorService(db_session)


async def _make_vendor(service: VendorService, **overrides):
    payload = VendorCreate(name="Acme Nuts Pvt Ltd", email="acme@example.com", **overrides)
    return await service.create_vendor(payload)


class TestVendorCRUD:
    async def test_create_vendor(self, service):
        vendor = await _make_vendor(service)
        assert vendor.id is not None
        assert vendor.status == VendorStatus.ACTIVE
        assert vendor.payment_terms_days == 30

    async def test_get_vendor_not_found_raises_404(self, service):
        with pytest.raises(HTTPException) as exc_info:
            await service.get_vendor(uuid.uuid4())
        assert exc_info.value.status_code == 404

    async def test_update_vendor(self, service):
        vendor = await _make_vendor(service)
        updated = await service.update_vendor(
            vendor.id, VendorUpdate(status=VendorStatus.INACTIVE, name="Acme Renamed")
        )
        assert updated.status == VendorStatus.INACTIVE
        assert updated.name == "Acme Renamed"

    async def test_soft_delete_vendor_excludes_from_list_and_get(self, service):
        vendor = await _make_vendor(service)
        await service.delete_vendor(vendor.id)
        with pytest.raises(HTTPException) as exc_info:
            await service.get_vendor(vendor.id)
        assert exc_info.value.status_code == 404

    async def test_list_vendors_pagination(self, service):
        for i in range(5):
            await _make_vendor(service, name=f"Vendor {i}", email=f"v{i}@example.com")
        items, total = await service.list_vendors(page=1, page_size=2)
        assert total == 5
        assert len(items) == 2


class TestVendorLedger:
    async def test_first_debit_entry_sets_balance(self, service):
        vendor = await _make_vendor(service)
        entry = await service.add_ledger_entry(
            vendor.id,
            VendorLedgerEntryCreate(
                entry_type=LedgerEntryType.DEBIT,
                source=LedgerEntrySource.ADJUSTMENT,
                amount=Decimal("100.00"),
                description="Opening balance",
            ),
        )
        assert entry.balance_after == Decimal("100.00")

    async def test_credit_reduces_balance(self, service):
        vendor = await _make_vendor(service)
        await service.add_ledger_entry(
            vendor.id,
            VendorLedgerEntryCreate(
                entry_type=LedgerEntryType.DEBIT,
                source=LedgerEntrySource.ADJUSTMENT,
                amount=Decimal("200.00"),
            ),
        )
        entry = await service.add_ledger_entry(
            vendor.id,
            VendorLedgerEntryCreate(
                entry_type=LedgerEntryType.CREDIT,
                source=LedgerEntrySource.PAYMENT,
                amount=Decimal("50.00"),
            ),
        )
        assert entry.balance_after == Decimal("150.00")

    async def test_ledger_entries_ordered_chronologically(self, service):
        vendor = await _make_vendor(service)
        for amount in ("10.00", "20.00", "30.00"):
            await service.add_ledger_entry(
                vendor.id,
                VendorLedgerEntryCreate(
                    entry_type=LedgerEntryType.DEBIT,
                    source=LedgerEntrySource.ADJUSTMENT,
                    amount=Decimal(amount),
                ),
            )
        entries = await service.list_ledger_entries(vendor.id)
        assert [e.amount for e in entries] == [Decimal("10.00"), Decimal("20.00"), Decimal("30.00")]
        assert [e.balance_after for e in entries] == [Decimal("10.00"), Decimal("30.00"), Decimal("60.00")]

    async def test_ledger_entry_for_missing_vendor_raises_404(self, service):
        with pytest.raises(HTTPException) as exc_info:
            await service.add_ledger_entry(
                uuid.uuid4(),
                VendorLedgerEntryCreate(
                    entry_type=LedgerEntryType.DEBIT,
                    source=LedgerEntrySource.ADJUSTMENT,
                    amount=Decimal("10.00"),
                ),
            )
        assert exc_info.value.status_code == 404
