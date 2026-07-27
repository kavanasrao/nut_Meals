"""Unit test for PDF generator — verifies output is valid PDF bytes."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.utils.pdf_generator import build_invoice_pdf


def _mock_invoice():
    return SimpleNamespace(
        invoice_number="NM-INV/2025-26/ABCD1234",
        order_id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        billing_name="Raj Sharma",
        billing_address="123 MG Road, Bengaluru",
        billing_gstin="29AABCU9603R1ZX",
        subtotal=Decimal("500.00"),
        discount_amount=Decimal("50.00"),
        cgst_rate=Decimal("9"),
        sgst_rate=Decimal("9"),
        igst_rate=Decimal("0"),
        cgst_amount=Decimal("40.50"),
        sgst_amount=Decimal("40.50"),
        igst_amount=Decimal("0"),
        total_amount=Decimal("531.00"),
        line_items=[
            {
                "product_id": str(uuid.uuid4()),
                "product_name": "Almond Butter 500g",
                "quantity": 2,
                "unit_price": "250.00",
                "tax_rate": "18",
                "line_total": "500.00",
            }
        ],
    )


def test_pdf_is_generated():
    """PDF is generated and starts with the PDF magic bytes."""
    pdf = build_invoice_pdf(_mock_invoice())
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000
    assert pdf[:4] == b"%PDF"


def test_pdf_is_larger_than_bare_minimum():
    """A real invoice PDF with line items should be at least 2 KB."""
    pdf = build_invoice_pdf(_mock_invoice())
    assert len(pdf) > 2000


def test_pdf_multiple_line_items():
    """PDF builds without error for multiple line items."""
    inv = _mock_invoice()
    inv.line_items = inv.line_items * 5   # 5 items
    pdf = build_invoice_pdf(inv)
    assert pdf[:4] == b"%PDF"
