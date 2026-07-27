"""initial procurement schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    vendor_status = postgresql.ENUM(
        "active", "inactive", "blacklisted", name="vendor_status"
    )
    po_status = postgresql.ENUM(
        "draft", "pending_approval", "approved", "rejected",
        "partially_received", "received", "closed", "cancelled",
        name="purchase_order_status",
    )
    grn_status = postgresql.ENUM("draft", "confirmed", "rejected", name="grn_status")
    invoice_status = postgresql.ENUM(
        "received", "matched", "disputed", "approved_for_payment", "paid", "cancelled",
        name="invoice_status",
    )
    ledger_entry_type = postgresql.ENUM("debit", "credit", name="ledger_entry_type")
    ledger_entry_source = postgresql.ENUM(
        "invoice", "payment", "adjustment", "opening_balance", name="ledger_entry_source"
    )

    bind = op.get_bind()
    for enum in (vendor_status, po_status, grn_status, invoice_status,
                 ledger_entry_type, ledger_entry_source):
        enum.create(bind, checkfirst=True)

    # --- vendors ---
    op.create_table(
        "vendors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("legal_name", sa.String(255)),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column("tax_id", sa.String(100)),
        sa.Column("address", sa.Text()),
        sa.Column("bank_account_number", sa.String(100)),
        sa.Column("bank_ifsc", sa.String(20)),
        sa.Column("payment_terms_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("status", vendor_status, nullable=False, server_default="active"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vendors_name", "vendors", ["name"])

    # --- vendor_ledger_entries ---
    op.create_table(
        "vendor_ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("entry_type", ledger_entry_type, nullable=False),
        sa.Column("source", ledger_entry_source, nullable=False),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(14, 2), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("finance_service_synced", sa.Boolean(), server_default="false"),
        sa.Column("finance_service_ref", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vendor_ledger_entries_vendor_id", "vendor_ledger_entries", ["vendor_id"])

    # --- purchase_orders ---
    op.create_table(
        "purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("po_number", sa.String(50), nullable=False, unique=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("status", po_status, nullable=False, server_default="draft"),
        sa.Column("expected_delivery_date", sa.Date()),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True)),
        sa.Column("approved_at", sa.String(50)),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_purchase_orders_po_number", "purchase_orders", ["po_number"])
    op.create_index("ix_purchase_orders_vendor_id", "purchase_orders", ["vendor_id"])
    op.create_index("ix_purchase_orders_status", "purchase_orders", ["status"])

    # --- purchase_order_items ---
    op.create_table(
        "purchase_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchase_orders.id"), nullable=False),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("quantity_ordered", sa.Integer(), nullable=False),
        sa.Column("quantity_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("tax_rate_percent", sa.Numeric(5, 2), server_default="0"),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_purchase_order_items_purchase_order_id", "purchase_order_items", ["purchase_order_id"])

    # --- goods_receipt_notes ---
    op.create_table(
        "goods_receipt_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("grn_number", sa.String(50), nullable=False, unique=True),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchase_orders.id"), nullable=False),
        sa.Column("status", grn_status, nullable=False, server_default="draft"),
        sa.Column("received_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("remarks", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_goods_receipt_notes_grn_number", "goods_receipt_notes", ["grn_number"])
    op.create_index("ix_goods_receipt_notes_purchase_order_id", "goods_receipt_notes", ["purchase_order_id"])

    # --- grn_items ---
    op.create_table(
        "grn_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("grn_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("goods_receipt_notes.id"), nullable=False),
        sa.Column("purchase_order_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchase_order_items.id"), nullable=False),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("quantity_received", sa.Integer(), nullable=False),
        sa.Column("quantity_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_grn_items_grn_id", "grn_items", ["grn_id"])

    # --- purchase_invoices ---
    op.create_table(
        "purchase_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("invoice_number", sa.String(100), nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchase_orders.id"), nullable=True),
        sa.Column("grn_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("goods_receipt_notes.id"), nullable=True),
        sa.Column("status", invoice_status, nullable=False, server_default="received"),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date()),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("amount_paid", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("file_url", sa.String(500)),
        sa.Column("reconciliation_notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_purchase_invoices_invoice_number", "purchase_invoices", ["invoice_number"])
    op.create_index("ix_purchase_invoices_vendor_id", "purchase_invoices", ["vendor_id"])
    op.create_index("ix_purchase_invoices_purchase_order_id", "purchase_invoices", ["purchase_order_id"])
    op.create_index("ix_purchase_invoices_status", "purchase_invoices", ["status"])
    op.create_unique_constraint(
        "uq_vendor_invoice_number", "purchase_invoices", ["vendor_id", "invoice_number"]
    )

    # --- purchase_invoice_items ---
    op.create_table(
        "purchase_invoice_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchase_invoices.id"), nullable=False),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("tax_rate_percent", sa.Numeric(5, 2), server_default="0"),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_purchase_invoice_items_invoice_id", "purchase_invoice_items", ["invoice_id"])


def downgrade() -> None:
    op.drop_table("purchase_invoice_items")
    op.drop_table("purchase_invoices")
    op.drop_table("grn_items")
    op.drop_table("goods_receipt_notes")
    op.drop_table("purchase_order_items")
    op.drop_table("purchase_orders")
    op.drop_table("vendor_ledger_entries")
    op.drop_table("vendors")

    bind = op.get_bind()
    for name in (
        "ledger_entry_source", "ledger_entry_type", "invoice_status",
        "grn_status", "purchase_order_status", "vendor_status",
    ):
        postgresql.ENUM(name=name).drop(bind, checkfirst=True)
