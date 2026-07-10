"""initial finance schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-10

Creates the full initial schema for the Finance service:
ledger_accounts, journal_entries, journal_lines, reconciliation_runs,
gateway_settlements, reconciliation_exceptions, audit_logs.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    account_type_enum = postgresql.ENUM(
        "asset", "liability", "equity", "income", "expense", name="account_type_enum", create_type=False
    )
    account_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "ledger_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("account_type", account_type_enum, nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_system_account", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ledger_accounts.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name="uq_ledger_accounts_code"),
    )
    op.create_index("ix_ledger_accounts_type", "ledger_accounts", ["account_type"])

    entry_status_enum = postgresql.ENUM("draft", "posted", "reversed", name="journal_entry_status_enum", create_type=False)
    entry_status_enum.create(op.get_bind(), checkfirst=True)
    source_type_enum = postgresql.ENUM(
        "order", "refund", "settlement", "manual_adjustment", "reconciliation", name="journal_source_type_enum", create_type=False
    )
    source_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entry_number", sa.String(30), nullable=False, unique=True),
        sa.Column("entry_date", sa.String(10), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("status", entry_status_enum, nullable=False, server_default="draft"),
        sa.Column("source_type", source_type_enum, nullable=False),
        sa.Column("source_reference", sa.String(100), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column("posted_by", sa.String(100), nullable=True),
        sa.Column("reversal_of_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal_entries.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_journal_entries_status", "journal_entries", ["status"])
    op.create_index("ix_journal_entries_source", "journal_entries", ["source_type", "source_reference"])
    op.create_index("ix_journal_entries_entry_date", "journal_entries", ["entry_date"])

    op.create_table(
        "journal_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "journal_entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("journal_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ledger_accounts.id"), nullable=False),
        sa.Column("line_number", sa.BigInteger, nullable=False),
        sa.Column("debit_amount_minor", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("credit_amount_minor", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("memo", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(debit_amount_minor > 0 AND credit_amount_minor = 0) OR "
            "(credit_amount_minor > 0 AND debit_amount_minor = 0)",
            name="ck_journal_line_single_sided",
        ),
        sa.CheckConstraint("debit_amount_minor >= 0 AND credit_amount_minor >= 0", name="ck_journal_line_non_negative"),
    )
    op.create_index("ix_journal_lines_entry", "journal_lines", ["journal_entry_id"])
    op.create_index("ix_journal_lines_account", "journal_lines", ["account_id"])

    provider_enum = postgresql.ENUM("juspay", "kotak_bank", "razorpay", "other", name="gateway_provider_enum", create_type=False)
    provider_enum.create(op.get_bind(), checkfirst=True)
    provider_enum_2 = postgresql.ENUM(
        "juspay", "kotak_bank", "razorpay", "other", name="gateway_provider_enum_2", create_type=False
    )
    provider_enum_2.create(op.get_bind(), checkfirst=True)
    run_status_enum = postgresql.ENUM("pending", "running", "completed", "failed", name="reconciliation_run_status_enum", create_type=False)
    run_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "reconciliation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", provider_enum, nullable=False),
        sa.Column("settlement_batch_id", sa.String(100), nullable=False),
        sa.Column("status", run_status_enum, nullable=False, server_default="pending"),
        sa.Column("total_records", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("matched_records", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("exception_records", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("triggered_by", sa.String(100), nullable=False, server_default="celery-beat"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    settlement_status_enum = postgresql.ENUM(
        "imported", "matched", "partially_matched", "mismatched", "unmatched", name="settlement_status_enum", create_type=False
    )
    settlement_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "gateway_settlements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reconciliation_runs.id"), nullable=False),
        sa.Column("provider", provider_enum_2, nullable=False),
        sa.Column("provider_transaction_id", sa.String(120), nullable=False),
        sa.Column("order_reference", sa.String(100), nullable=True),
        sa.Column("settled_amount_minor", sa.BigInteger, nullable=False),
        sa.Column("settlement_date", sa.String(10), nullable=False),
        sa.Column("fee_amount_minor", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("status", settlement_status_enum, nullable=False, server_default="imported"),
        sa.Column("raw_payload", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "provider_transaction_id", name="uq_settlement_provider_txn"),
    )
    op.create_index("ix_gateway_settlements_status", "gateway_settlements", ["status"])
    op.create_index("ix_gateway_settlements_order_ref", "gateway_settlements", ["order_reference"])

    op.create_table(
        "reconciliation_exceptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "settlement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("gateway_settlements.id"), nullable=False, unique=True
        ),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("expected_amount_minor", sa.BigInteger, nullable=True),
        sa.Column("actual_amount_minor", sa.BigInteger, nullable=True),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("resolved_by", sa.String(100), nullable=True),
        sa.Column("resolution_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recon_exceptions_resolved", "reconciliation_exceptions", ["resolved"])

    audit_action_enum = postgresql.ENUM(
        "journal_entry_created",
        "journal_entry_posted",
        "journal_entry_reversed",
        "ledger_account_created",
        "ledger_account_updated",
        "settlement_imported",
        "reconciliation_run_started",
        "reconciliation_run_completed",
        "reconciliation_exception_resolved",
        "report_exported",
        name="audit_action_enum",
        create_type=False,
    )
    audit_action_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("action", audit_action_enum, nullable=False),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_actor", "audit_logs", ["actor"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("reconciliation_exceptions")
    op.drop_table("gateway_settlements")
    op.drop_table("reconciliation_runs")
    op.drop_table("journal_lines")
    op.drop_table("journal_entries")
    op.drop_table("ledger_accounts")

    bind = op.get_bind()
    for enum_name in (
        "audit_action_enum",
        "settlement_status_enum",
        "reconciliation_run_status_enum",
        "gateway_provider_enum_2",
        "gateway_provider_enum",
        "journal_source_type_enum",
        "journal_entry_status_enum",
        "account_type_enum",
    ):
        postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)
