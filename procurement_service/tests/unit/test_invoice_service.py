import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.base import InvoiceStatus, PurchaseOrderStatus
from app.schemas.grn import GRNCreate, GRNItemCreate
from app.schemas.invoice import PurchaseInvoiceCreate, PurchaseInvoiceItemCreate
from app.schemas.purchase_order import (
    PurchaseOrderApproval,
    PurchaseOrderCreate,
    PurchaseOrderItemCreate,
)
from app.schemas.vendor import VendorCreate
from app.services.grn_service import GRNService
from app.services.invoice_service import InvoiceService
from app.services.po_service import PurchaseOrderService
from app.services.vendor_service import VendorService

pytestmark = pytest.mark.unit


@pytest.fixture
def vendor_service(db_session):
    return VendorService(db_session)


@pytest.fixture
def po_service(db_session):
    return PurchaseOrderService(db_session)


@pytest.fixture
def grn_service(db_session):
    return GRNService(db_session)


@pytest.fixture
def invoice_service(db_session, mock_finance_client):
    service = InvoiceService(db_session)
    service.ledger_service.finance_client = mock_finance_client
    return service


async def _setup_received_po(vendor_service, po_service, grn_service, qty=20):
    vendor = await vendor_service.create_vendor(
        VendorCreate(name="Invoice Vendor", email="iv@example.com")
    )
    po = await po_service.create_po(
        PurchaseOrderCreate(
            vendor_id=vendor.id,
            items=[
                PurchaseOrderItemCreate(
                    sku="SKU-INV", quantity_ordered=qty, unit_price=Decimal("5.00")
                )
            ],
        ),
        created_by=uuid.uuid4(),
    )
    po = await po_service.approve_or_reject_po(
        po.id, PurchaseOrderApproval(approve=True), uuid.uuid4()
    )
    grn = await grn_service.create_grn(
        GRNCreate(
            purchase_order_id=po.id,
            items=[
                GRNItemCreate(
                    purchase_order_item_id=po.items[0].id, sku="SKU-INV", quantity_received=qty
                )
            ],
        ),
        received_by=uuid.uuid4(),
    )
    return vendor, po, grn


class TestInvoiceCreation:
    async def test_create_invoice_computes_totals_and_books_ledger(
        self, invoice_service, vendor_service, mock_finance_client
    ):
        vendor = await vendor_service.create_vendor(
            VendorCreate(name="Simple Vendor", email="simple@example.com")
        )
        invoice = await invoice_service.create_invoice(
            PurchaseInvoiceCreate(
                invoice_number="INV-001",
                vendor_id=vendor.id,
                invoice_date=date.today(),
                items=[
                    PurchaseInvoiceItemCreate(
                        sku="SKU-X", quantity=2, unit_price=Decimal("50.00"),
                        tax_rate_percent=Decimal("18"),
                    )
                ],
            )
        )
        assert invoice.subtotal == Decimal("100.00")
        assert invoice.tax_amount == Decimal("18.00")
        assert invoice.total_amount == Decimal("118.00")
        mock_finance_client.post_journal_entry.assert_awaited_once()

        # Invoice booking posts a CREDIT (source=INVOICE); by convention CREDIT
        # decreases the ledger balance, so a negative balance represents the
        # amount currently owed to the vendor (accounts payable).
        balance = await vendor_service.get_current_balance(vendor.id)
        assert balance == Decimal("-118.00")

    async def test_duplicate_invoice_number_for_same_vendor_rejected(
        self, invoice_service, vendor_service
    ):
        vendor = await vendor_service.create_vendor(
            VendorCreate(name="Dup Vendor", email="dup@example.com")
        )
        payload = PurchaseInvoiceCreate(
            invoice_number="INV-DUP",
            vendor_id=vendor.id,
            invoice_date=date.today(),
            items=[PurchaseInvoiceItemCreate(sku="A", quantity=1, unit_price=Decimal("1.00"))],
        )
        await invoice_service.create_invoice(payload)
        with pytest.raises(HTTPException) as exc_info:
            await invoice_service.create_invoice(payload)
        assert exc_info.value.status_code == 409


class TestThreeWayMatch:
    async def test_matching_invoice_marks_matched(
        self, invoice_service, vendor_service, po_service, grn_service
    ):
        vendor, po, grn = await _setup_received_po(vendor_service, po_service, grn_service, qty=20)
        invoice = await invoice_service.create_invoice(
            PurchaseInvoiceCreate(
                invoice_number="INV-MATCH",
                vendor_id=vendor.id,
                purchase_order_id=po.id,
                grn_id=grn.id,
                invoice_date=date.today(),
                items=[
                    PurchaseInvoiceItemCreate(sku="SKU-INV", quantity=20, unit_price=Decimal("5.00"))
                ],
            )
        )
        result = await invoice_service.match_against_grn(invoice.id)
        assert result.status == InvoiceStatus.MATCHED

    async def test_over_invoiced_quantity_marks_disputed(
        self, invoice_service, vendor_service, po_service, grn_service
    ):
        vendor, po, grn = await _setup_received_po(vendor_service, po_service, grn_service, qty=20)
        invoice = await invoice_service.create_invoice(
            PurchaseInvoiceCreate(
                invoice_number="INV-DISPUTE",
                vendor_id=vendor.id,
                purchase_order_id=po.id,
                grn_id=grn.id,
                invoice_date=date.today(),
                items=[
                    # invoiced more than received
                    PurchaseInvoiceItemCreate(sku="SKU-INV", quantity=999, unit_price=Decimal("5.00"))
                ],
            )
        )
        result = await invoice_service.match_against_grn(invoice.id)
        assert result.status == InvoiceStatus.DISPUTED
        assert "SKU-INV" in result.reconciliation_notes

    async def test_missing_po_or_grn_marks_disputed(self, invoice_service, vendor_service):
        vendor = await vendor_service.create_vendor(
            VendorCreate(name="No PO Vendor", email="nopo@example.com")
        )
        invoice = await invoice_service.create_invoice(
            PurchaseInvoiceCreate(
                invoice_number="INV-NOPO",
                vendor_id=vendor.id,
                invoice_date=date.today(),
                items=[PurchaseInvoiceItemCreate(sku="A", quantity=1, unit_price=Decimal("1.00"))],
            )
        )
        result = await invoice_service.match_against_grn(invoice.id)
        assert result.status == InvoiceStatus.DISPUTED
