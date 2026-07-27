from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.purchase_order import PurchaseOrderApproval, PurchaseOrderCreate
from app.schemas.vendor import VendorCreate

pytestmark = pytest.mark.unit


class TestVendorSchema:
    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            VendorCreate(name="X", email="not-an-email")

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            VendorCreate(name="")

    def test_payment_terms_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            VendorCreate(name="X", payment_terms_days=400)


class TestPurchaseOrderSchema:
    def test_requires_at_least_one_item(self):
        with pytest.raises(ValidationError):
            PurchaseOrderCreate(vendor_id="11111111-1111-1111-1111-111111111111", items=[])

    def test_negative_quantity_rejected(self):
        with pytest.raises(ValidationError):
            PurchaseOrderCreate(
                vendor_id="11111111-1111-1111-1111-111111111111",
                items=[
                    {
                        "sku": "A",
                        "quantity_ordered": -5,
                        "unit_price": Decimal("1.00"),
                    }
                ],
            )

    def test_approval_reject_without_reason_fails(self):
        with pytest.raises(ValidationError):
            PurchaseOrderApproval(approve=False)

    def test_approval_reject_with_reason_succeeds(self):
        approval = PurchaseOrderApproval(approve=False, rejection_reason="Budget exceeded")
        assert approval.rejection_reason == "Budget exceeded"

    def test_approval_true_does_not_require_reason(self):
        approval = PurchaseOrderApproval(approve=True)
        assert approval.rejection_reason is None
