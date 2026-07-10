"""Tests for sitemap generation service and API routes."""
from datetime import datetime, timezone

import pytest

from app.models.sitemap import ChangeFrequency, SitemapEntityType
from app.services.sitemap_service import SitemapService, render_urlset


@pytest.mark.asyncio
async def test_upsert_entry_creates_new_entry(db_session):
    service = SitemapService(db_session)
    entry = await service.upsert_entry(
        entity_type=SitemapEntityType.PRODUCT,
        entity_id="prod-1",
        loc="https://www.nutmeals.com/products/almonds",
        lastmod=datetime.now(timezone.utc),
        changefreq=ChangeFrequency.DAILY,
        priority=0.8,
    )
    assert entry.id is not None
    assert entry.entity_id == "prod-1"
    assert entry.is_active is True


@pytest.mark.asyncio
async def test_upsert_entry_updates_existing(db_session):
    service = SitemapService(db_session)
    await service.upsert_entry(
        entity_type=SitemapEntityType.PRODUCT,
        entity_id="prod-1",
        loc="https://www.nutmeals.com/products/almonds",
        lastmod=datetime.now(timezone.utc),
        changefreq=ChangeFrequency.DAILY,
        priority=0.8,
    )
    updated = await service.upsert_entry(
        entity_type=SitemapEntityType.PRODUCT,
        entity_id="prod-1",
        loc="https://www.nutmeals.com/products/roasted-almonds",
        lastmod=datetime.now(timezone.utc),
        changefreq=ChangeFrequency.WEEKLY,
        priority=0.5,
    )
    assert updated.loc == "https://www.nutmeals.com/products/roasted-almonds"
    assert updated.changefreq == ChangeFrequency.WEEKLY


@pytest.mark.asyncio
async def test_deactivate_entry_excludes_from_generated_file(db_session):
    service = SitemapService(db_session)
    await service.upsert_entry(
        entity_type=SitemapEntityType.PRODUCT,
        entity_id="prod-1",
        loc="https://www.nutmeals.com/products/almonds",
        lastmod=datetime.now(timezone.utc),
        changefreq=ChangeFrequency.DAILY,
        priority=0.8,
    )
    await service.deactivate_entry(SitemapEntityType.PRODUCT, "prod-1")
    files = await service.generate_files_for_type(SitemapEntityType.PRODUCT)
    assert files[0].url_count == 0


@pytest.mark.asyncio
async def test_generate_files_paginates_beyond_limit(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.sitemap_service.settings.SITEMAP_MAX_URLS_PER_FILE", 2
    )
    service = SitemapService(db_session)
    for i in range(5):
        await service.upsert_entry(
            entity_type=SitemapEntityType.PRODUCT,
            entity_id=f"prod-{i}",
            loc=f"https://www.nutmeals.com/products/item-{i}",
            lastmod=datetime.now(timezone.utc),
            changefreq=ChangeFrequency.DAILY,
            priority=0.5,
        )
    files = await service.generate_files_for_type(SitemapEntityType.PRODUCT)
    assert len(files) == 3  # 5 entries / 2 per file -> 3 files
    assert sum(f.url_count for f in files) == 5


def test_render_urlset_escapes_special_characters():
    from app.models.sitemap import SitemapEntry

    entry = SitemapEntry(
        entity_type=SitemapEntityType.PRODUCT,
        entity_id="prod-1",
        loc="https://www.nutmeals.com/products/nuts&berries",
        lastmod=datetime.now(timezone.utc),
        changefreq=ChangeFrequency.DAILY,
        priority=0.8,
    )
    xml = render_urlset([entry])
    assert "&amp;" in xml
    assert "<urlset" in xml


@pytest.mark.asyncio
async def test_get_sitemap_index_404_when_not_generated(anon_client):
    response = await anon_client.get("/sitemaps/sitemap-index.xml")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_sitemap_index_returns_xml(anon_client, db_session):
    service = SitemapService(db_session)
    await service.regenerate_index()
    await db_session.commit()

    response = await anon_client.get("/sitemaps/sitemap-index.xml")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "<sitemapindex" in response.text


@pytest.mark.asyncio
async def test_rebuild_sitemap_requires_auth(anon_client):
    response = await anon_client.post("/sitemaps/rebuild", json={"force": False})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_rebuild_sitemap_queues_task(client, monkeypatch):
    class FakeAsyncResult:
        id = "task-123"

    monkeypatch.setattr(
        "app.api.routes_sitemap.rebuild_sitemap_task.delay",
        lambda *a, **kw: FakeAsyncResult(),
    )
    response = await client.post("/sitemaps/rebuild", json={"force": True})
    assert response.status_code == 202
    body = response.json()
    assert body["task_id"] == "task-123"
    assert body["status"] == "queued"
