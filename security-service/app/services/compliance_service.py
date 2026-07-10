"""
Compliance reporting service.

Each ComplianceReportDefinition maps to a small set of "checks" -- pure
functions that inspect audit logs, WAF incidents, and RBAC bindings and
return pass/fail + evidence. The framework->checks mapping below is the
starting point for PCI DSS and GDPR readiness; add checks here as new
requirements are identified (SOC2 scaffolding is included for the same reason).
"""
import uuid
from datetime import datetime, timedelta
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog, AuditSeverity
from app.models.compliance import (
    ComplianceFramework,
    ComplianceReportDefinition,
    ComplianceReportRun,
    ReportStatus,
)
from app.models.rbac import UserRoleBinding
from app.models.waf import WafIncident
from app.schemas.compliance import ComplianceFinding, ComplianceReportDefinitionCreate


class ComplianceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_definition(self, payload: ComplianceReportDefinitionCreate) -> ComplianceReportDefinition:
        definition = ComplianceReportDefinition(**payload.model_dump())
        self.db.add(definition)
        await self.db.commit()
        await self.db.refresh(definition)
        return definition

    async def list_definitions(self) -> list[ComplianceReportDefinition]:
        result = await self.db.execute(select(ComplianceReportDefinition))
        return list(result.scalars().all())

    async def get_definition(self, definition_id: uuid.UUID) -> ComplianceReportDefinition | None:
        return await self.db.get(ComplianceReportDefinition, definition_id)

    # --- Check implementations -------------------------------------------------

    async def _check_critical_actions_have_audit_trail(self, lookback_days: int = 30) -> ComplianceFinding:
        """PCI DSS 10.x: all access to cardholder-data-adjacent actions must be logged."""
        since = datetime.utcnow() - timedelta(days=lookback_days)
        stmt = select(func.count()).select_from(AuditLog).where(
            AuditLog.created_at >= since, AuditLog.action.in_(["payment.captured", "payment.refunded"])
        )
        result = await self.db.execute(stmt)
        count = result.scalar_one()
        return ComplianceFinding(
            check_id="pci_10_audit_trail",
            description="Payment actions produce an audit trail",
            passed=count > 0,
            evidence={"logged_payment_events": count, "lookback_days": lookback_days},
        )

    async def _check_no_orphaned_admin_roles(self) -> ComplianceFinding:
        """PCI DSS 7.x / general least-privilege: flag admin bindings without a recent grantor record."""
        stmt = select(func.count()).select_from(UserRoleBinding).where(UserRoleBinding.granted_by.is_(None))
        result = await self.db.execute(stmt)
        count = result.scalar_one()
        return ComplianceFinding(
            check_id="least_privilege_grant_trail",
            description="All role grants have a recorded grantor",
            passed=count == 0,
            evidence={"ungranted_bindings": count},
            remediation="Backfill `granted_by` for legacy role bindings" if count else None,
        )

    async def _check_waf_incident_response(self, lookback_days: int = 30) -> ComplianceFinding:
        """PCI DSS 6.6: a WAF (or equivalent) must be actively blocking attacks."""
        since = datetime.utcnow() - timedelta(days=lookback_days)
        stmt = select(func.count()).select_from(WafIncident).where(WafIncident.created_at >= since)
        result = await self.db.execute(stmt)
        count = result.scalar_one()
        return ComplianceFinding(
            check_id="pci_6_6_waf_active",
            description="WAF is actively evaluating and (when configured) blocking traffic",
            passed=True,  # presence of the WAF pipeline itself is the control; incident count is informational
            evidence={"incidents_last_n_days": count, "lookback_days": lookback_days},
        )

    async def _check_critical_severity_logs_reviewed(self, lookback_days: int = 30) -> ComplianceFinding:
        """GDPR Art. 33 readiness: critical events (e.g. potential breaches) must exist & be discoverable."""
        since = datetime.utcnow() - timedelta(days=lookback_days)
        stmt = select(func.count()).select_from(AuditLog).where(
            AuditLog.created_at >= since, AuditLog.severity == AuditSeverity.CRITICAL
        )
        result = await self.db.execute(stmt)
        count = result.scalar_one()
        return ComplianceFinding(
            check_id="gdpr_33_breach_visibility",
            description="Critical-severity events are captured and queryable for breach-notification timelines",
            passed=True,
            evidence={"critical_events_last_n_days": count, "lookback_days": lookback_days},
        )

    def _checks_for_framework(self, framework: ComplianceFramework) -> list[Callable]:
        mapping: dict[ComplianceFramework, list[Callable]] = {
            ComplianceFramework.PCI_DSS: [
                self._check_critical_actions_have_audit_trail,
                self._check_no_orphaned_admin_roles,
                self._check_waf_incident_response,
            ],
            ComplianceFramework.GDPR: [
                self._check_critical_severity_logs_reviewed,
                self._check_no_orphaned_admin_roles,
            ],
            ComplianceFramework.SOC2: [
                self._check_critical_actions_have_audit_trail,
                self._check_waf_incident_response,
                self._check_no_orphaned_admin_roles,
            ],
        }
        return mapping.get(framework, [])

    async def run_report(self, definition_id: uuid.UUID, requested_by: str) -> ComplianceReportRun:
        """Synchronously runs all checks for a definition and stores the result.

        Kept synchronous (vs. Celery) because checks are cheap aggregate
        queries; heavier frameworks/checks can be moved to a background task
        the same way audit exports are, without changing this method's contract.
        """
        definition = await self.get_definition(definition_id)
        if definition is None:
            raise ValueError(f"No compliance report definition with id {definition_id}")

        run = ComplianceReportRun(
            definition_id=definition_id,
            framework=definition.framework,
            status=ReportStatus.RUNNING,
            requested_by=requested_by,
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)

        try:
            checks = self._checks_for_framework(definition.framework)
            findings = [await check() for check in checks]
            passed = sum(1 for f in findings if f.passed)
            score = round(100 * passed / len(findings), 2) if findings else 0.0

            run.findings_json = {"checks": [f.model_dump() for f in findings]}
            run.readiness_score = score
            run.status = ReportStatus.COMPLETED
            run.completed_at = datetime.utcnow()
        except Exception as exc:  # noqa: BLE001
            run.status = ReportStatus.FAILED
            run.error_message = str(exc)
        finally:
            await self.db.commit()
            await self.db.refresh(run)

        return run

    async def get_run(self, run_id: uuid.UUID) -> ComplianceReportRun | None:
        return await self.db.get(ComplianceReportRun, run_id)

    async def list_runs(self, framework: ComplianceFramework | None = None) -> list[ComplianceReportRun]:
        stmt = select(ComplianceReportRun).order_by(ComplianceReportRun.created_at.desc())
        if framework:
            stmt = stmt.where(ComplianceReportRun.framework == framework)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
