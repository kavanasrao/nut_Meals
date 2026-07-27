import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.base import PurchaseOrderStatus
from app.schemas.grn import GRNCreate, GRNItemCreate
from app.schemas.purchase_order import (
    PurchaseOrderApproval,
    PurchaseOrderCreate,
    PurchaseOrderItemCreate,
)
from app.schemas.vendor import VendorCreate
from app.services.grn_service import GRNService
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


async def _make_vendor(vendor_service):
    return await vendor_service.create_vendor(
        VendorCreate(name="Supplier Co", email="s@example.com")
    )


async def _make_po(po_service, vendor_id, qty=100, price="10.00", created_by=None):
    payload = PurchaseOrderCreate(
        vendor_id=vendor_id,
        items=[
            PurchaseOrderItemCreate(
                sku="SKU-001",
                quantity_ordered=qty,
                unit_price=Decimal(price),
                tax_rate_percent=Decimal("10"),
            )
        ],
    )
    return await po_service.create_po(payload, created_by=created_by or uuid.uuid4())


class TestPurchaseOrderService:
    async def test_create_po_computes_totals(self, po_service, vendor_service):
        vendor = await _make_vendor(vendor_service)
        po = await _make_po(po_service, vendor.id, qty=10, price="10.00")
        # subtotal = 100, tax = 10 (10%), total = 110
        assert po.subtotal == Decimal("100.00")
        assert po.tax_amount == Decimal("10.00")
        assert po.total_amount == Decimal("110.00")
        assert po.status == PurchaseOrderStatus.PENDING_APPROVAL

    async def test_create_po_invalid_vendor_raises_404(self, po_service):
        with pytest.raises(HTTPException) as exc_info:
            await _make_po(po_service, uuid.uuid4())
        assert exc_info.value.status_code == 404

    async def test_approve_po(self, po_service, vendor_service):
        vendor = await _make_vendor(vendor_service)
        po = await _make_po(po_service, vendor.id)
        approver_id = uuid.uuid4()
        approved = await po_service.approve_or_reject_po(
            po.id, PurchaseOrderApproval(approve=True), approver_id
        )
        assert approved.status == PurchaseOrderStatus.APPROVED
        assert approved.approved_by == approver_id

    async def test_reject_po_requires_reason(self):
        with pytest.raises(ValueError):
            PurchaseOrderApproval(approve=False)

    async def test_cannot_approve_twice(self, po_service, vendor_service):
        vendor = await _make_vendor(vendor_service)
        po = await _make_po(po_service, vendor.id)
        await po_service.approve_or_reject_po(
            po.id, PurchaseOrderApproval(approve=True), uuid.uuid4()
        )
        with pytest.raises(HTTPException) as exc_info:
            await po_service.approve_or_reject_po(
                po.id, PurchaseOrderApproval(approve=True), uuid.uuid4()
            )
        assert exc_info.value.status_code == 409


class TestGRNService:
    async def test_create_grn_updates_po_item_and_status(
        self, po_service, grn_service, vendor_service
    ):
        vendor = await _make_vendor(vendor_service)
        po = await _make_po(po_service, vendor.id, qty=100)
        await po_service.approve_or_reject_po(
            po.id, PurchaseOrderApproval(approve=True), uuid.uuid4()
        )
        po_item_id = po.items[0].id

        grn = await grn_service.create_grn(
            GRNCreate(
                purchase_order_id=po.id,
                items=[
                    GRNItemCreate(
                        purchase_order_item_id=po_item_id, sku="SKU-001", quantity_received=40
                    )
                ],
            ),
            received_by=uuid.uuid4(),
        )
        assert grn.items[0].quantity_received == 40

        refreshed_po = await po_service.get_po(po.id)
        assert refreshed_po.status == PurchaseOrderStatus.PARTIALLY_RECEIVED
        assert refreshed_po.items[0].quantity_received == 40

    async def test_full_receipt_marks_po_received(
        self, po_service, grn_service, vendor_service
    ):
        vendor = await _make_vendor(vendor_service)
        po = await _make_po(po_service, vendor.id, qty=50)
        await po_service.approve_or_reject_po(
            po.id, PurchaseOrderApproval(approve=True), uuid.uuid4()
        )
        po_item_id = po.items[0].id

        await grn_service.create_grn(
            GRNCreate(
                purchase_order_id=po.id,
                items=[
                    GRNItemCreate(
                        purchase_order_item_id=po_item_id, sku="SKU-001", quantity_received=50
                    )
                ],
            ),
            received_by=uuid.uuid4(),
        )
        refreshed_po = await po_service.get_po(po.id)
        assert refreshed_po.status == PurchaseOrderStatus.RECEIVED

    async def test_over_receiving_rejected(self, po_service, grn_service, vendor_service):
        vendor = await _make_vendor(vendor_service)
        po = await _make_po(po_service, vendor.id, qty=10)
        await po_service.approve_or_reject_po(
            po.id, PurchaseOrderApproval(approve=True), uuid.uuid4()
        )
        po_item_id = po.items[0].id

        with pytest.raises(HTTPException) as exc_info:
            await grn_service.create_grn(
                GRNCreate(
                    purchase_order_id=po.id,
                    items=[
                        GRNItemCreate(
                            purchase_order_item_id=po_item_id, sku="SKU-001", quantity_received=999
                        )
                    ],
                ),
                received_by=uuid.uuid4(),
            )
        assert exc_info.value.status_code == 400

    async def test_receiving_against_unapproved_po_rejected(
        self, po_service, grn_service, vendor_service
    ):
        vendor = await _make_vendor(vendor_service)
        po = await _make_po(po_service, vendor.id, qty=10)  # still pending_approval
        po_item_id = po.items[0].id

        with pytest.raises(HTTPException) as exc_info:
            await grn_service.create_grn(
                GRNCreate(
                    purchase_order_id=po.id,
                    items=[
                        GRNItemCreate(
                            purchase_order_item_id=po_item_id, sku="SKU-001", quantity_received=5
                        )
                    ],
                ),
                received_by=uuid.uuid4(),
            )
        assert exc_info.value.status_code == 409
