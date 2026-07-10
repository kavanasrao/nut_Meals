"""initial security service schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- RBAC ---
    op.create_table(
        "roles",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system_role", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_roles_name", "roles", ["name"])

    op.create_table(
        "permissions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("service", sa.String(64), nullable=False),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"])
    op.create_index("ix_permissions_service", "permissions", ["service"])

    op.create_table(
        "role_permissions",
        sa.Column("role_id", pg.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "permission_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("permissions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "user_role_bindings",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("role_id", pg.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("granted_by", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )
    op.create_index("ix_user_role_bindings_user_id", "user_role_bindings", ["user_id"])

    # --- WAF ---
    waf_rule_type = pg.ENUM(
        "sql_injection", "xss", "csrf", "rate_limit", "custom_regex", "ip_blocklist",
        name="wafruletype",
    )
    waf_action = pg.ENUM("block", "log_only", "challenge", name="wafaction")
    waf_rule_type.create(op.get_bind(), checkfirst=True)
    waf_action.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "waf_rules",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("rule_type", waf_rule_type, nullable=False),
        sa.Column("pattern", sa.Text(), nullable=False),
        sa.Column("action", waf_action, nullable=False, server_default="block"),
        sa.Column("severity", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("applies_to_service", sa.String(64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_waf_rules_rule_type", "waf_rules", ["rule_type"])
    op.create_index("ix_waf_rules_is_active", "waf_rules", ["is_active"])

    op.create_table(
        "waf_incidents",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("rule_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("rule_name", sa.String(128), nullable=False),
        sa.Column("rule_type", waf_rule_type, nullable=False),
        sa.Column("action_taken", waf_action, nullable=False),
        sa.Column("source_ip", sa.String(64), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("service", sa.String(64), nullable=False),
        sa.Column("matched_fragment", sa.Text(), nullable=True),
        sa.Column("user_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_waf_incidents_rule_id", "waf_incidents", ["rule_id"])
    op.create_index("ix_waf_incidents_source_ip", "waf_incidents", ["source_ip"])
    op.create_index("ix_waf_incidents_service", "waf_incidents", ["service"])
    op.create_index("ix_waf_incidents_user_id", "waf_incidents", ["user_id"])
    op.create_index("ix_waf_incidents_created_at", "waf_incidents", ["created_at"])

    # --- Audit ---
    audit_severity = pg.ENUM("info", "warning", "critical", name="auditseverity")
    audit_severity.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("service", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(128), nullable=True),
        sa.Column("severity", audit_severity, nullable=False, server_default="info"),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("metadata_json", pg.JSONB(), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_service", "audit_logs", ["service"])
    op.create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"])
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_service_created", "audit_logs", ["service", "created_at"])
    op.create_index("ix_audit_logs_action_created", "audit_logs", ["action", "created_at"])

    op.create_table(
        "audit_export_jobs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("requested_by", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("filters_json", pg.JSONB(), nullable=True),
        sa.Column("result_path", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- Compliance ---
    framework_enum = pg.ENUM("pci_dss", "gdpr", "soc2", name="complianceframework")
    status_enum = pg.ENUM("pending", "running", "completed", "failed", name="reportstatus")
    framework_enum.create(op.get_bind(), checkfirst=True)
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "compliance_report_definitions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("framework", framework_enum, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("check_config_json", pg.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_compliance_report_definitions_framework", "compliance_report_definitions", ["framework"])

    op.create_table(
        "compliance_report_runs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("definition_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("framework", framework_enum, nullable=False),
        sa.Column("status", status_enum, nullable=False, server_default="pending"),
        sa.Column("requested_by", sa.String(128), nullable=False),
        sa.Column("readiness_score", sa.Float(), nullable=True),
        sa.Column("findings_json", pg.JSONB(), nullable=True),
        sa.Column("export_path", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_compliance_report_runs_definition_id", "compliance_report_runs", ["definition_id"])
    op.create_index("ix_compliance_report_runs_framework", "compliance_report_runs", ["framework"])
    op.create_index("ix_compliance_report_runs_status", "compliance_report_runs", ["status"])
    op.create_index("ix_compliance_report_runs_created_at", "compliance_report_runs", ["created_at"])


def downgrade() -> None:
    op.drop_table("compliance_report_runs")
    op.drop_table("compliance_report_definitions")
    op.drop_table("audit_export_jobs")
    op.drop_table("audit_logs")
    op.drop_table("waf_incidents")
    op.drop_table("waf_rules")
    op.drop_table("user_role_bindings")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")

    bind = op.get_bind()
    pg.ENUM(name="reportstatus").drop(bind, checkfirst=True)
    pg.ENUM(name="complianceframework").drop(bind, checkfirst=True)
    pg.ENUM(name="auditseverity").drop(bind, checkfirst=True)
    pg.ENUM(name="wafaction").drop(bind, checkfirst=True)
    pg.ENUM(name="wafruletype").drop(bind, checkfirst=True)
