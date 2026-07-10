"""Import all models so Alembic autogenerate / Base.metadata sees them."""
from app.models.rbac import Role, Permission, RolePermission, UserRoleBinding, RoleName  # noqa: F401
from app.models.waf import WafRule, WafIncident, WafRuleType, WafAction  # noqa: F401
from app.models.audit import AuditLog, AuditExportJob, AuditSeverity  # noqa: F401
from app.models.compliance import (  # noqa: F401
    ComplianceReportDefinition,
    ComplianceReportRun,
    ComplianceFramework,
    ReportStatus,
)
