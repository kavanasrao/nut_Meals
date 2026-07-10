"""initial schema: gift_orders, subscriptions, saved_addresses,
saved_payment_methods, one_click_tokens

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

gift_wrap_option = postgresql.ENUM("none", "standard", "premium", name="gift_wrap_option")
subscription_frequency = postgresql.ENUM("weekly", "monthly", name="subscription_frequency")
subscription_status = postgresql.ENUM(
    "active", "paused", "cancelled", "past_due", "expired", name="subscription_status"
)


def upgrade() -> None:
    bind = op.get_bind()
    gift_wrap_option.create(bind, checkfirst=True)
    subscription_frequency.create(bind, checkfirst=True)
    subscription_status.create(bind, checkfirst=True)

    op.create_table(
        "gift_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_gift", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("gift_message", sa.Text(), nullable=True),
        sa.Column("recipient_name", sa.String(255), nullable=False),
        sa.Column("recipient_email", sa.String(255), nullable=True),
        sa.Column("recipient_phone", sa.String(32), nullable=True),
        sa.Column("recipient_address_line1", sa.String(255), nullable=False),
        sa.Column("recipient_address_line2", sa.String(255), nullable=True),
        sa.Column("recipient_city", sa.String(120), nullable=False),
        sa.Column("recipient_state", sa.String(120), nullable=False),
        sa.Column("recipient_postal_code", sa.String(20), nullable=False),
        sa.Column("recipient_country", sa.String(2), nullable=False, server_default="US"),
        sa.Column("gift_wrap_option", gift_wrap_option, nullable=False, server_default="none"),
        sa.Column("scheduled_delivery_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notify_recipient", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notification_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_gift_orders_order_id", "gift_orders", ["order_id"])
    op.create_index("ix_gift_orders_customer_id", "gift_orders", ["customer_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", sa.String(64), nullable=False),
        sa.Column("plan_snapshot", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("frequency", subscription_frequency, nullable=False),
        sa.Column("status", subscription_status, nullable=False, server_default="active"),
        sa.Column("price_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("payment_method_token", sa.String(255), nullable=False),
        sa.Column("shipping_address_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("next_renewal_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_renewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_renewal_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("renewal_notice_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_subscriptions_customer_id", "subscriptions", ["customer_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_index("ix_subscriptions_next_renewal_date", "subscriptions", ["next_renewal_date"])

    op.create_table(
        "saved_addresses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(64), server_default="Home"),
        sa.Column("line1", sa.String(255), nullable=False),
        sa.Column("line2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("state", sa.String(120), nullable=False),
        sa.Column("postal_code", sa.String(20), nullable=False),
        sa.Column("country", sa.String(2), nullable=False, server_default="US"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_saved_addresses_customer_id", "saved_addresses", ["customer_id"])

    op.create_table(
        "saved_payment_methods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processor_token", sa.String(255), nullable=False),
        sa.Column("brand", sa.String(32), nullable=True),
        sa.Column("last4", sa.String(4), nullable=True),
        sa.Column("exp_month", sa.Integer(), nullable=True),
        sa.Column("exp_year", sa.Integer(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_saved_payment_methods_customer_id", "saved_payment_methods", ["customer_id"])

    op.create_table(
        "one_click_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_one_click_tokens_customer_id", "one_click_tokens", ["customer_id"])
    op.create_index("ix_one_click_tokens_token_hash", "one_click_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("one_click_tokens")
    op.drop_table("saved_payment_methods")
    op.drop_table("saved_addresses")
    op.drop_table("subscriptions")
    op.drop_table("gift_orders")

    bind = op.get_bind()
    subscription_status.drop(bind, checkfirst=True)
    subscription_frequency.drop(bind, checkfirst=True)
    gift_wrap_option.drop(bind, checkfirst=True)
