import pytest


@pytest.mark.asyncio
async def test_audit_logs_requires_auditor_role(client, auth_headers):
    # auth_headers uses `notifier` role, not permitted for audit reads
    resp = await client.get("/api/v1/audit/logs", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_logs_accessible_to_auditor(client, auditor_token):
    resp = await client.get("/api/v1/audit/logs", headers={"Authorization": f"Bearer {auditor_token}"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_compliance_report_csv(client, auditor_token):
    resp = await client.post(
        "/api/v1/audit/compliance-report",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={
            "start_date": "2026-01-01T00:00:00Z",
            "end_date": "2026-12-31T00:00:00Z",
            "export_format": "csv",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")


@pytest.mark.asyncio
async def test_compliance_report_json(client, auditor_token):
    resp = await client.post(
        "/api/v1/audit/compliance-report",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={
            "start_date": "2026-01-01T00:00:00Z",
            "end_date": "2026-12-31T00:00:00Z",
            "export_format": "json",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == []
