"""initial schema for admin cms service

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

content_status_enum = postgresql.ENUM(
    "draft", "scheduled", "published", "archived", name="contentstatus"
)
content_type_enum = postgresql.ENUM(
    "blog_post", "announcement", "faq", name="contenttype"
)
return_status_enum = postgresql.ENUM(
    "pending", "approved", "rejected", "resolved", name="returnstatus"
)
return_tier_enum = postgresql.ENUM("A", "B", "C", name="returntier")


def upgrade() -> None:
    bind = op.get_bind()
    content_status_enum.create(bind, checkfirst=True)
    content_type_enum.create(bind, checkfirst=True)
    return_status_enum.create(bind, checkfirst=True)
    return_tier_enum.create(bind, checkfirst=True)

    # --- content_items ---
    op.create_table(
        "content_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("content_type", content_type_enum, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.String(500), nullable=True),
        sa.Column("status", content_status_enum, nullable=False, server_default="draft"),
        sa.Column("publish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("seo_title", sa.String(70), nullable=True),
        sa.Column("seo_description", sa.String(160), nullable=True),
        sa.Column("seo_keywords", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("og_image_url", sa.String(500), nullable=True),
        sa.Column("canonical_url", sa.String(500), nullable=True),
        sa.Column("author_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_content_items_status_publish_at", "content_items", ["status", "publish_at"])
    op.create_index("ix_content_items_slug", "content_items", ["slug"], unique=True)

    # --- content_revisions ---
    op.create_table(
        "content_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "content_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("edited_by_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
    )

    # --- return_requests ---
    op.create_table(
        "return_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("reason_detail", sa.Text(), nullable=True),
        sa.Column("status", return_status_enum, nullable=False, server_default="pending"),
        sa.Column("tier", return_tier_enum, nullable=False, server_default="A"),
        sa.Column("refund_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("restock_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("logistics_reference", sa.String(120), nullable=True),
        sa.Column("decided_by_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_return_requests_status", "return_requests", ["status"])
    op.create_index("ix_return_requests_order_id", "return_requests", ["order_id"])

    # --- return_events ---
    op.create_table(
        "return_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "return_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("return_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", return_status_enum, nullable=True),
        sa.Column("to_status", return_status_enum, nullable=False),
        sa.Column("actor_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    # --- finance_summary_cache ---
    op.create_table(
        "finance_summary_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("granularity", sa.String(20), nullable=False),
        sa.Column("total_revenue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total_expenses", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("net_profit", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("breakdown_json", postgresql.JSONB(), nullable=True),
        sa.Column("source_snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("period_start", "period_end", "granularity", name="uq_finance_period"),
    )

    # --- finance_report_exports ---
    op.create_table(
        "finance_report_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("requested_by_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("file_url", sa.String(500), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
    )

    # --- kpi_snapshots ---
    op.create_table(
        "kpi_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("total_orders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_visitors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversion_rate", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("new_customers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repeat_customers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repeat_customer_rate", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("churned_customers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("churn_rate", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("gross_merchandise_value", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("average_order_value", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("low_stock_sku_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_metrics_json", postgresql.JSONB(), nullable=True),
        sa.UniqueConstraint("snapshot_date", name="uq_kpi_snapshot_date"),
    )

    # --- audit_log_entries ---
    op.create_table(
        "audit_log_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actor_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_role", sa.String(50), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("request_ip", postgresql.INET(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("audit_log_entries")
    op.drop_table("kpi_snapshots")
    op.drop_table("finance_report_exports")
    op.drop_table("finance_summary_cache")
    op.drop_table("return_events")
    op.drop_table("return_requests")
    op.drop_table("content_revisions")
    op.drop_table("content_items")

    bind = op.get_bind()
    return_tier_enum.drop(bind, checkfirst=True)
    return_status_enum.drop(bind, checkfirst=True)
    content_type_enum.drop(bind, checkfirst=True)
    content_status_enum.drop(bind, checkfirst=True)
