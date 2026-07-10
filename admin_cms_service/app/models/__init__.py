"""
Import all ORM models here so Alembic's autogenerate can discover them
via Base.metadata, and so application code can `from app import models`.
"""
from app.models.analytics import KPISnapshot  # noqa: F401
from app.models.audit import AuditLogEntry  # noqa: F401
from app.models.content import ContentItem, ContentRevision  # noqa: F401
from app.models.finance import FinanceReportExport, FinanceSummaryCache  # noqa: F401
from app.models.returns import ReturnEvent, ReturnRequest  # noqa: F401

__all__ = [
    "KPISnapshot",
    "AuditLogEntry",
    "ContentItem",
    "ContentRevision",
    "FinanceReportExport",
    "FinanceSummaryCache",
    "ReturnEvent",
    "ReturnRequest",
]
