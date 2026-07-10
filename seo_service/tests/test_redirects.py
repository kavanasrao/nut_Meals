"""Tests for redirect rules, canonical URLs, and RBAC enforcement."""
import pytest

from app.core.security import CurrentUser, Role, get_current_user
from app.main import app
from app.services.redirect_service import RedirectService


@pytest.mark.asyncio
async def test_create_and_lookup_redirect(db_session):
    service = RedirectService(db_session)
    await service.create_rule(
        source_path="/old-product-slug",
        target_path="/products/new-product-slug",
        redirect_type=301,
        reason="slug change",
    )
    rule = await service.lookup_by_source("/old-product-slug")
    assert rule is not None
    assert rule.target_path == "/products/new-product-slug"


@pytest.mark.asyncio
async def test_lookup_missing_redirect_returns_none(db_session):
    service = RedirectService(db_session)
    rule = await service.lookup_by_source("/nonexistent")
    assert rule is None


@pytest.mark.asyncio
async def test_sync_from_catalog_upserts_rules(db_session):
    service = RedirectService(db_session)
    catalog_rules = [
        {"source_path": "/a", "target_path": "/b", "redirect_type": 301},
        {"source_path": "/c", "target_path": "/d", "redirect_type": 302},
    ]
    synced = await service.sync_from_catalog(catalog_rules)
    assert synced == 2
    rule = await service.lookup_by_source("/a")
    assert rule.synced_from_catalog is True


@pytest.mark.asyncio
async def test_upsert_canonical_creates_then_updates(db_session):
    service = RedirectService(db_session)
    canonical = await service.upsert_canonical(
        entity_type="product", entity_id="prod-1", canonical_path="/products/almonds"
    )
    assert canonical.canonical_path == "/products/almonds"

    updated = await service.upsert_canonical(
        entity_type="product", entity_id="prod-1", canonical_path="/products/almonds-500g"
    )
    assert updated.id == canonical.id
    assert updated.canonical_path == "/products/almonds-500g"


@pytest.mark.asyncio
async def test_lookup_redirect_endpoint_public(anon_client, db_session):
    service = RedirectService(db_session)
    await service.create_rule(
        source_path="/old-page", target_path="/new-page", redirect_type=301, reason=None
    )
    await db_session.commit()

    response = await anon_client.get("/redirects/lookup", params={"source_path": "/old-page"})
    assert response.status_code == 200
    assert response.json()["target_path"] == "/new-page"


@pytest.mark.asyncio
async def test_create_redirect_endpoint_requires_editor_role(db_session):
    """A VIEWER role should be forbidden from creating redirect rules."""
    from httpx import ASGITransport, AsyncClient

    from app.database import get_db

    viewer = CurrentUser(subject="viewer-1", role=Role.VIEWER, raw_claims={})

    async def _get_db_override():
        yield db_session

    async def _get_current_user_override():
        return viewer

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = _get_current_user_override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/redirects",
            json={"source_path": "/x", "target_path": "/y", "redirect_type": 301},
        )
    app.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_redirect_endpoint_as_admin_writes_audit_log(client, db_session):
    response = await client.post(
        "/redirects",
        json={"source_path": "/old", "target_path": "/new", "redirect_type": 301},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["source_path"] == "/old"

    from sqlalchemy import select

    from app.models.ai_discovery import AuditLogEntry

    result = await db_session.execute(select(AuditLogEntry))
    entries = result.scalars().all()
    assert any(e.action == "redirect.create" for e in entries)


@pytest.mark.asyncio
async def test_upsert_canonical_endpoint(client):
    response = await client.put(
        "/redirects/canonical",
        json={
            "entity_type": "product",
            "entity_id": "prod-1",
            "canonical_path": "/products/almonds",
        },
    )
    assert response.status_code == 200
    assert response.json()["canonical_path"] == "/products/almonds"


@pytest.mark.asyncio
async def test_get_canonical_404_when_absent(anon_client):
    response = await anon_client.get(
        "/redirects/canonical", params={"entity_type": "product", "entity_id": "missing"}
    )
    assert response.status_code == 404
