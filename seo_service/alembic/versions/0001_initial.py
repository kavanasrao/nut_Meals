"""initial SEO service schema

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

sitemap_entity_type = postgresql.ENUM(
    "product", "category", "blog_post", "static_page", name="sitemap_entity_type"
)
sitemap_changefreq = postgresql.ENUM(
    "always", "hourly", "daily", "weekly", "monthly", "yearly", "never",
    name="sitemap_changefreq",
)
schema_type_enum = postgresql.ENUM(
    "Product", "Review", "AggregateRating", "BlogPosting", "BreadcrumbList",
    "Organization", "FAQPage", name="schema_type",
)
ai_export_status = postgresql.ENUM(
    "pending", "running", "complete", "failed", name="ai_export_status"
)


def upgrade() -> None:
    bind = op.get_bind()
    sitemap_entity_type.create(bind, checkfirst=True)
    sitemap_changefreq.create(bind, checkfirst=True)
    schema_type_enum.create(bind, checkfirst=True)
    ai_export_status.create(bind, checkfirst=True)

    op.create_table(
        "sitemap_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sitemap_entity_type, nullable=False),
        sa.Column("entity_id", sa.String(128), nullable=False),
        sa.Column("loc", sa.Text, nullable=False),
        sa.Column("lastmod", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changefreq", sitemap_changefreq, nullable=False, server_default="weekly"),
        sa.Column("priority", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_sitemap_entries_entity", "sitemap_entries", ["entity_type", "entity_id"], unique=True
    )
    op.create_index(
        "ix_sitemap_entries_type_updated", "sitemap_entries", ["entity_type", "updated_at"]
    )

    op.create_table(
        "sitemap_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("entity_type", sitemap_entity_type, nullable=True),
        sa.Column("part_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("url_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("xml_content", sa.Text, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "structured_data_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(128), nullable=False),
        sa.Column("schema_type", schema_type_enum, nullable=False),
        sa.Column("json_ld", postgresql.JSONB, nullable=False),
        sa.Column("schema_version", sa.String(16), nullable=False, server_default="1.0"),
        sa.Column("is_valid", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("validation_errors", postgresql.JSONB, nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_structured_data_entity_schema",
        "structured_data_records",
        ["entity_type", "entity_id", "schema_type"],
        unique=True,
    )

    op.create_table(
        "redirect_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_path", sa.String(2048), nullable=False),
        sa.Column("target_path", sa.String(2048), nullable=False),
        sa.Column("redirect_type", sa.Integer, nullable=False, server_default="301"),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("hit_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("synced_from_catalog", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_redirect_rules_source_path", "redirect_rules", ["source_path"], unique=True
    )

    op.create_table(
        "canonical_urls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(128), nullable=False),
        sa.Column("canonical_path", sa.Text, nullable=False),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_canonical_urls_entity", "canonical_urls", ["entity_type", "entity_id"], unique=True
    )

    op.create_table(
        "ai_export_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", ai_export_status, nullable=False, server_default="pending"),
        sa.Column("file_path", sa.String(512), nullable=True),
        sa.Column("record_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("requested_by", sa.String(128), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "audit_log_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_subject", sa.String(128), nullable=False),
        sa.Column("actor_role", sa.String(64), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("target_type", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(128), nullable=True),
        sa.Column("before_state", postgresql.JSONB, nullable=True),
        sa.Column("after_state", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_log_entries")
    op.drop_table("ai_export_batches")
    op.drop_table("canonical_urls")
    op.drop_table("redirect_rules")
    op.drop_table("structured_data_records")
    op.drop_table("sitemap_files")
    op.drop_table("sitemap_entries")

    bind = op.get_bind()
    ai_export_status.drop(bind, checkfirst=True)
    schema_type_enum.drop(bind, checkfirst=True)
    sitemap_changefreq.drop(bind, checkfirst=True)
    sitemap_entity_type.drop(bind, checkfirst=True)
