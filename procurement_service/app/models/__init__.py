"""
Import all models here so Alembic's autogenerate (via Base.metadata) can
discover every table. Do not remove imports even if they look unused.
"""
from app.models.vendor import Vendor, VendorLedgerEntry  # noqa: F401
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem  # noqa: F401
from app.models.grn import GoodsReceiptNote, GRNItem  # noqa: F401
from app.models.invoice import PurchaseInvoice, PurchaseInvoiceItem  # noqa: F401

__all__ = [
    "Vendor",
    "VendorLedgerEntry",
    "PurchaseOrder",
    "PurchaseOrderItem",
    "GoodsReceiptNote",
    "GRNItem",
    "PurchaseInvoice",
    "PurchaseInvoiceItem",
]
