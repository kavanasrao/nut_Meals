"""initial inventory schema

Revision ID: 0001
Revises:
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

movement_type_enum = postgresql.ENUM(
    "inbound", "outbound", "transfer_in", "transfer_out",
    "production_consume", "production_yield", "reservation_hold",
    "reservation_release", "adjustment",
    name="movementtype",
)
batch_status_enum = postgresql.ENUM(
    "planned", "in_progress", "completed", "cancelled", "failed",
    name="batchstatus",
)
reservation_status_enum = postgresql.ENUM(
    "active", "confirmed", "released", "expired",
    name="reservationstatus",
)


def upgrade() -> None:
    bind = op.get_bind()
    movement_type_enum.create(bind, checkfirst=True)
    batch_status_enum.create(bind, checkfirst=True)
    reservation_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "warehouses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("location", sa.String(256), nullable=False),
        sa.Column("capacity_units", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_warehouses_code", "warehouses", ["code"])

    op.create_table(
        "items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sku", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("unit_of_measure", sa.String(16), nullable=False, server_default="unit"),
        sa.Column("is_finished_product", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("reorder_threshold", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_items_sku", "items", ["sku"])

    op.create_table(
        "stock_levels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity_on_hand", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("quantity_reserved", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("warehouse_id", "item_id", name="uq_stock_wh_item"),
    )

    op.create_table(
        "stock_transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("source_warehouse_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("destination_warehouse_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("lot_number", sa.String(64), nullable=True),
        sa.Column("initiated_by", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="completed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "stock_movement_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("movement_type", movement_type_enum, nullable=False),
        sa.Column("quantity_delta", sa.Numeric(14, 3), nullable=False),
        sa.Column("lot_number", sa.String(64), nullable=True),
        sa.Column("reference_id", sa.String(64), nullable=True),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("notes", sa.String(512), nullable=True),
    )
    op.create_index("ix_movement_logs_item", "stock_movement_logs", ["item_id"])
    op.create_index("ix_movement_logs_lot", "stock_movement_logs", ["lot_number"])

    op.create_table(
        "bill_of_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("yield_quantity", sa.Numeric(14, 3), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("product_item_id", "version", name="uq_bom_product_version"),
    )

    op.create_table(
        "bom_components",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bom_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("bill_of_materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("quantity_required", sa.Numeric(14, 3), nullable=False),
    )

    op.create_table(
        "production_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("batch_number", sa.String(64), nullable=False, unique=True),
        sa.Column("bom_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bill_of_materials.id"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("planned_quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("actual_yield_quantity", sa.Numeric(14, 3), nullable=True),
        sa.Column("lot_number", sa.String(64), nullable=False),
        sa.Column("status", batch_status_enum, nullable=False, server_default="planned"),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_batches_number", "production_batches", ["batch_number"])
    op.create_index("ix_batches_lot", "production_batches", ["lot_number"])

    op.create_table(
        "stock_reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", sa.String(64), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("status", reservation_status_enum, nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_reservations_order", "stock_reservations", ["order_id"])


def downgrade() -> None:
    op.drop_table("stock_reservations")
    op.drop_table("production_batches")
    op.drop_table("bom_components")
    op.drop_table("bill_of_materials")
    op.drop_table("stock_movement_logs")
    op.drop_table("stock_transfers")
    op.drop_table("stock_levels")
    op.drop_table("items")
    op.drop_table("warehouses")

    bind = op.get_bind()
    reservation_status_enum.drop(bind, checkfirst=True)
    batch_status_enum.drop(bind, checkfirst=True)
    movement_type_enum.drop(bind, checkfirst=True)
