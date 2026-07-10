"""initial logistics schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

carrier_code_enum = postgresql.ENUM("delhivery", "india_post", name="carriercode")
shipment_status_enum = postgresql.ENUM(
    "created", "picked_up", "in_transit", "out_for_delivery",
    "delivered", "failed", "return_to_origin", "cancelled",
    name="shipmentstatus",
)
shipment_type_enum = postgresql.ENUM("forward", "reverse", name="shipmenttype")


def upgrade() -> None:
    bind = op.get_bind()
    carrier_code_enum.create(bind, checkfirst=True)
    shipment_status_enum.create(bind, checkfirst=True)
    shipment_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "carriers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", carrier_code_enum, nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("avg_cost_per_kg", sa.Float(), server_default="0"),
        sa.Column("avg_delivery_hours", sa.Float(), server_default="0"),
        sa.Column("reliability_score", sa.Float(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "shipments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("carrier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("carriers.id"), nullable=False),
        sa.Column("carrier_awb", sa.String(64), unique=True, nullable=True),
        sa.Column("shipment_type", shipment_type_enum, server_default="forward"),
        sa.Column("status", shipment_status_enum, server_default="created"),
        sa.Column("origin_pincode", sa.String(10), nullable=False),
        sa.Column("destination_pincode", sa.String(10), nullable=False),
        sa.Column("weight_kg", sa.Numeric(6, 2), server_default="0"),
        sa.Column("cod_amount", sa.Numeric(10, 2), server_default="0"),
        sa.Column("meta", sa.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_shipments_order_id", "shipments", ["order_id"])

    op.create_table(
        "tracking_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shipments.id"), nullable=False),
        sa.Column("status", shipment_status_enum, nullable=False),
        sa.Column("location", sa.String(128), nullable=True),
        sa.Column("remarks", sa.String(255), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload", sa.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tracking_events_shipment_id", "tracking_events", ["shipment_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("details", sa.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_index("ix_tracking_events_shipment_id", table_name="tracking_events")
    op.drop_table("tracking_events")
    op.drop_index("ix_shipments_order_id", table_name="shipments")
    op.drop_table("shipments")
    op.drop_table("carriers")

    bind = op.get_bind()
    shipment_type_enum.drop(bind, checkfirst=True)
    shipment_status_enum.drop(bind, checkfirst=True)
    carrier_code_enum.drop(bind, checkfirst=True)
