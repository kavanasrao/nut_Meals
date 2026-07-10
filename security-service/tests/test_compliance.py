"""Unit tests for ComplianceService checks + integration tests for the /compliance API."""
import pytest

from app.models.compliance import ComplianceFramework
from app.schemas.audit import AuditLogCreate
from app.schemas.compliance import ComplianceReportDefinitionCreate
from app.services.audit_service import AuditService
from app.services.compliance_service import ComplianceService
from tests.conftest import auth_headers


@pytest.mark.asyncio
class TestComplianceService:
    async def test_create_and_list_definitions(self, db_session):
        service = ComplianceService(db_session)
        definition = await service.create_definition(
            ComplianceReportDefinitionCreate(
                name="PCI Quarterly Review",
                framework=ComplianceFramework.PCI_DSS,
                description="Quarterly PCI DSS readiness check",
            )
        )
        assert definition.id is not None

        definitions = await service.list_definitions()
        assert any(d.name == "PCI Quarterly Review" for d in definitions)

    async def test_run_report_computes_readiness_score(self, db_session):
        audit_service = AuditService(db_session)
        await audit_service.create_log(AuditLogCreate(action="payment.captured", service="payments"))

        compliance_service = ComplianceService(db_session)
        definition = await compliance_service.create_definition(
            ComplianceReportDefinitionCreate(name="PCI Run Test", framework=ComplianceFramework.PCI_DSS)
        )
        run = await compliance_service.run_report(definition.id, requested_by="auditor-1")

        assert run.status.value == "completed"
        assert run.readiness_score is not None
        assert 0 <= run.readiness_score <= 100
        assert "checks" in run.findings_json

    async def test_run_report_raises_for_unknown_definition(self, db_session):
        import uuid

        compliance_service = ComplianceService(db_session)
        with pytest.raises(ValueError):
            await compliance_service.run_report(uuid.uuid4(), requested_by="auditor-1")

    async def test_gdpr_framework_uses_different_checks(self, db_session):
        compliance_service = ComplianceService(db_session)
        definition = await compliance_service.create_definition(
            ComplianceReportDefinitionCreate(name="GDPR Readiness", framework=ComplianceFramework.GDPR)
        )
        run = await compliance_service.run_report(definition.id, requested_by="auditor-1")
        check_ids = [c["check_id"] for c in run.findings_json["checks"]]
        assert "gdpr_33_breach_visibility" in check_ids
        assert "pci_6_6_waf_active" not in check_ids


@pytest.mark.asyncio
class TestComplianceApi:
    async def test_run_report_requires_permission(self, client, db_session):
        import uuid

        resp = await client.post(
            "/compliance/reports/run",
            json={"definition_id": str(uuid.uuid4())},
            headers=auth_headers(user_id="no-permissions-user"),
        )
        assert resp.status_code == 403

    async def test_full_definition_to_run_flow(self, client, db_session, admin_user):
        create_resp = await client.post(
            "/compliance/definitions",
            json={"name": "PCI API Test", "framework": "pci_dss", "description": "test"},
            headers=auth_headers(user_id=admin_user),
        )
        assert create_resp.status_code == 200
        definition_id = create_resp.json()["id"]

        run_resp = await client.post(
            "/compliance/reports/run",
            json={"definition_id": definition_id},
            headers=auth_headers(user_id=admin_user),
        )
        assert run_resp.status_code == 200
        assert run_resp.json()["status"] == "completed"

        list_resp = await client.get(
            "/compliance/reports/runs", params={"framework": "pci_dss"}, headers=auth_headers(user_id=admin_user)
        )
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1
