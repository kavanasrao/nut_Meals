"""Aggregates all ORM models so Alembic autogenerate can see them."""
from app.models.ai_discovery import AiExportBatch, AuditLogEntry, ExportStatus
from app.models.redirects import CanonicalUrl, RedirectRule, RedirectType
from app.models.sitemap import ChangeFrequency, SitemapEntityType, SitemapEntry, SitemapFile
from app.models.structured_data import SchemaType, StructuredDataRecord

__all__ = [
    "AiExportBatch",
    "AuditLogEntry",
    "ExportStatus",
    "CanonicalUrl",
    "RedirectRule",
    "RedirectType",
    "ChangeFrequency",
    "SitemapEntityType",
    "SitemapEntry",
    "SitemapFile",
    "SchemaType",
    "StructuredDataRecord",
]
