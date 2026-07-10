"""Unit tests for AuditService + integration tests for the /audit API."""
import pytest

from app.schemas.audit import AuditLogCreate, AuditLogFilter
from app.services.audit_service import AuditService
from app.tasks.audit_tasks import run_audit_export
from tests.conftest import auth_headers


@pytest.fixture(autouse=True)
def run_celery_tasks_eagerly(monkeypatch):
    """Route .delay() calls to Celery's synchronous .apply() so tests don't
    require a live broker; the task body still runs exactly as in production."""
    monkeypatch.setattr(run_audit_export, "delay", lambda job_id: run_audit_export.apply(args=[job_id]))


@pytest.mark.asyncio
class TestAuditService:
    async def test_create_log_persists_record(self, db_session):
        service = AuditService(db_session)
        log = await service.create_log(
            AuditLogCreate(user_id="user-1", action="order.created", service="orders", resource_id="ord-1")
        )
        assert log.id is not None
        assert log.action == "order.created"

    async def test_list_logs_filters_by_service(self, db_session):
        service = AuditService(db_session)
        await service.create_log(AuditLogCreate(action="order.created", service="orders"))
        await service.create_log(AuditLogCreate(action="payment.captured", service="payments"))

        orders_only = await service.list_logs(AuditLogFilter(service="orders", limit=10, offset=0))
        assert all(log.service == "orders" for log in orders_only)
        assert len(orders_only) == 1

    async def test_list_logs_filters_by_date_range(self, db_session):
        from datetime import datetime, timedelta

        service = AuditService(db_session)
        await service.create_log(AuditLogCreate(action="inventory.adjusted", service="inventory"))

        future_start = datetime.utcnow() + timedelta(days=1)
        results = await service.list_logs(
            AuditLogFilter(start_date=future_start, limit=10, offset=0)
        )
        assert results == []

    async def test_bulk_create_inserts_all(self, db_session):
        service = AuditService(db_session)
        payloads = [
            AuditLogCreate(action="order.created", service="orders"),
            AuditLogCreate(action="order.cancelled", service="orders"),
        ]
        count = await service.bulk_create(payloads)
        assert count == 2

    async def test_export_job_lifecycle_completes(self, db_session):
        service = AuditService(db_session)
        await service.create_log(AuditLogCreate(action="order.created", service="orders"))

        job = await service.create_export_job("auditor-1", AuditLogFilter(service="orders", limit=100, offset=0))
        assert job.status == "pending"

        await service.run_export(job.id)
        refreshed = await service.get_export_job(job.id)
        assert refreshed.status == "completed"
        assert refreshed.result_path is not None


@pytest.mark.asyncio
class TestAuditApi:
    async def test_create_log_requires_permission(self, client, db_session):
        resp = await client.post(
            "/audit/logs",
            json={"action": "order.created", "service": "orders"},
            headers=auth_headers(user_id="no-permissions-user"),
        )
        assert resp.status_code == 403

    async def test_create_and_list_logs(self, client, db_session, admin_user):
        create_resp = await client.post(
            "/audit/logs",
            json={"action": "order.created", "service": "orders", "user_id": "cust-1"},
            headers=auth_headers(user_id=admin_user),
        )
        assert create_resp.status_code == 201

        list_resp = await client.get(
            "/audit/logs", params={"service": "orders"}, headers=auth_headers(user_id=admin_user)
        )
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1

    async def test_export_job_flow(self, client, db_session, admin_user):
        export_resp = await client.post(
            "/audit/logs/export",
            json={"filters": {"service": "orders", "limit": 100, "offset": 0}, "format": "csv"},
            headers=auth_headers(user_id=admin_user),
        )
        assert export_resp.status_code == 202
        job_id = export_resp.json()["id"]

        status_resp = await client.get(
            f"/audit/logs/export/{job_id}", headers=auth_headers(user_id=admin_user)
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] in ("pending", "running", "completed", "failed")
