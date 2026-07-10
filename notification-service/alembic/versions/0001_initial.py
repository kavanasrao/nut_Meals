"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

message_channel_enum = postgresql.ENUM(
    "email", "sms", "push", "whatsapp", "webhook", name="messagechannel"
)
message_status_enum = postgresql.ENUM(
    "pending", "processing", "sent", "failed", "dead", "cancelled", name="messagestatus"
)
outbox_status_enum = postgresql.ENUM("new", "published", "failed", name="outboxstatus")


def upgrade() -> None:
    bind = op.get_bind()
    message_channel_enum.create(bind, checkfirst=True)
    message_status_enum.create(bind, checkfirst=True)
    outbox_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("channel", message_channel_enum, nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", message_status_enum, nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False, unique=True),
        sa.Column("correlation_id", sa.String(255), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_messages_status_channel", "messages", ["status", "channel"])
    op.create_index("ix_messages_recipient", "messages", ["recipient"])

    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("aggregate_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_payload", sa.JSON(), nullable=False),
        sa.Column("status", outbox_status_enum, nullable=False, server_default="new"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "dead_letters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id"), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("payload_snapshot", sa.JSON(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("reprocessed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reprocessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reprocessed_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor", sa.String(255), nullable=False, server_default="system"),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("channel", sa.String(50), nullable=True),
        sa.Column("recipient", sa.String(255), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "retry_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("channel", sa.String(50), nullable=False, unique=True),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("base_backoff_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("max_backoff_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("jitter", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_table("retry_policies")
    op.drop_table("audit_logs")
    op.drop_table("dead_letters")
    op.drop_table("outbox_events")
    op.drop_index("ix_messages_recipient", table_name="messages")
    op.drop_index("ix_messages_status_channel", table_name="messages")
    op.drop_table("messages")

    bind = op.get_bind()
    outbox_status_enum.drop(bind, checkfirst=True)
    message_status_enum.drop(bind, checkfirst=True)
    message_channel_enum.drop(bind, checkfirst=True)
