"""Initial schema — carts, wishlists, coupons, addresses, invoices.

Revision ID: 0001
Revises:
Create Date: 2025-07-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "carts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("coupon_code", sa.String(64), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("recovery_email_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_carts_user_id", "carts", ["user_id"], unique=True)

    op.create_table(
        "cart_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cart_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("carts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("image_url", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cart_items_cart_id", "cart_items", ["cart_id"])

    op.create_table(
        "wishlist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("image_url", sa.String(512), nullable=True),
        sa.Column("unit_price", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "product_id", name="uq_wishlist_user_product"),
    )
    op.create_index("ix_wishlist_items_user_id", "wishlist_items", ["user_id"])

    op.create_table(
        "coupons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("discount_type", sa.Enum("percent", "fixed", name="discounttype"), nullable=False),
        sa.Column("discount_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("min_order_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_discount_cap", sa.Numeric(10, 2), nullable=True),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("per_user_limit", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_coupon_code"),
    )
    op.create_index("ix_coupons_code", "coupons", ["code"])

    op.create_table(
        "coupon_usages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("coupon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("times_used", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("coupon_id", "user_id", name="uq_coupon_usage_user"),
    )

    op.create_table(
        "saved_addresses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("full_name", sa.String(128), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("line1", sa.String(255), nullable=False),
        sa.Column("line2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("state", sa.String(100), nullable=False),
        sa.Column("pincode", sa.String(10), nullable=False),
        sa.Column("country", sa.String(64), nullable=False, server_default="India"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("gstin", sa.String(15), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_saved_addresses_user_id", "saved_addresses", ["user_id"])

    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("invoice_number", sa.String(64), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("billing_name", sa.String(128), nullable=False),
        sa.Column("billing_address", sa.String(512), nullable=False),
        sa.Column("billing_gstin", sa.String(15), nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("cgst_rate", sa.Numeric(5, 2), nullable=False, server_default="9"),
        sa.Column("sgst_rate", sa.Numeric(5, 2), nullable=False, server_default="9"),
        sa.Column("igst_rate", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("cgst_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("sgst_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("igst_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_items", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.Enum("pending", "generated", "failed", "sent",
                                    name="invoicestatus"), nullable=False, server_default="pending"),
        sa.Column("pdf_url", sa.String(512), nullable=True),
        sa.Column("celery_task_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("invoice_number", name="uq_invoice_number"),
    )
    op.create_index("ix_invoices_order_id", "invoices", ["order_id"])
    op.create_index("ix_invoices_user_id", "invoices", ["user_id"])


def downgrade() -> None:
    op.drop_table("invoices")
    op.execute("DROP TYPE IF EXISTS invoicestatus")
    op.drop_table("saved_addresses")
    op.drop_table("coupon_usages")
    op.drop_table("coupons")
    op.execute("DROP TYPE IF EXISTS discounttype")
    op.drop_table("wishlist_items")
    op.drop_table("cart_items")
    op.drop_table("carts")
