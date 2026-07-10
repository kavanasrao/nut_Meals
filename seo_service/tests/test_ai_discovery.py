"""Tests for AI discovery metadata endpoints and export batch service."""
import pytest
import respx
from httpx import Response

from app.config import get_settings
from app.models.ai_discovery import ExportStatus
from app.services.ai_discovery_service import AiDiscoveryService, build_product_embedding_metadata

settings = get_settings()

SAMPLE_PRODUCT = {
    "id": "prod-1",
    "name": "Roasted Almonds 500g",
    "description": "Premium roasted almonds, lightly salted.",
    "category_name": "Nuts & Snacks",
    "tags": ["snack", "protein", "keto-friendly"],
    "brand": "nut_Meals",
    "price": 9.99,
    "currency": "USD",
    "in_stock": True,
    "dietary_tags": ["gluten-free", "vegan"],
    "canonical_url": "https://www.nutmeals.com/products/roasted-almonds-500g",
    "images": ["https://cdn.nutmeals.com/almonds.jpg"],
    "updated_at": "2026-06-01T00:00:00Z",
}


def test_build_product_embedding_metadata_shape():
    metadata = build_product_embedding_metadata(SAMPLE_PRODUCT)
    assert metadata["type"] == "product"
    assert "Roasted Almonds" in metadata["text"]
    assert metadata["facets"]["brand"] == "nut_Meals"
    assert metadata["facets"]["dietary_tags"] == ["gluten-free", "vegan"]
    assert metadata["image"] == "https://cdn.nutmeals.com/almonds.jpg"


def test_build_product_embedding_metadata_handles_missing_optional_fields():
    minimal = {"id": "prod-2", "name": "Cashews", "canonical_url": "https://x/cashews"}
    metadata = build_product_embedding_metadata(minimal)
    assert metadata["facets"]["dietary_tags"] == []
    assert metadata["image"] is None


@pytest.mark.asyncio
async def test_export_batch_lifecycle(db_session):
    service = AiDiscoveryService(db_session)
    batch = await service.create_batch(requested_by="tester")
    assert batch.status == ExportStatus.PENDING

    await service.mark_running(str(batch.id))
    refreshed = await service.get_batch(str(batch.id))
    assert refreshed.status == ExportStatus.RUNNING

    ndjson = AiDiscoveryService.to_ndjson([{"id": "prod-1"}])
    await service.mark_complete(
        str(batch.id), file_path="/tmp/export.ndjson", record_count=1, ndjson_bytes=ndjson
    )
    completed = await service.get_batch(str(batch.id))
    assert completed.status == ExportStatus.COMPLETE
    assert completed.record_count == 1
    assert completed.checksum_sha256 is not None


@pytest.mark.asyncio
async def test_export_batch_marked_failed_on_error(db_session):
    service = AiDiscoveryService(db_session)
    batch = await service.create_batch()
    await service.mark_failed(str(batch.id), "upstream timeout")
    failed = await service.get_batch(str(batch.id))
    assert failed.status == ExportStatus.FAILED
    assert failed.error_message == "upstream timeout"


def test_to_ndjson_produces_valid_lines():
    ndjson = AiDiscoveryService.to_ndjson([{"a": 1}, {"b": 2}])
    lines = ndjson.decode("utf-8").strip().split("\n")
    assert len(lines) == 2
    assert lines[0] == '{"a":1}'


@pytest.mark.asyncio
async def test_get_product_ai_metadata_endpoint(anon_client):
    with respx.mock(base_url=settings.CATALOG_SERVICE_URL) as mock:
        mock.get("/internal/products/prod-1").mock(
            return_value=Response(200, json=SAMPLE_PRODUCT)
        )
        response = await anon_client.get("/ai-discovery/products/prod-1/metadata")
    assert response.status_code == 200
    assert response.json()["facets"]["brand"] == "nut_Meals"


@pytest.mark.asyncio
async def test_get_product_ai_metadata_returns_502_on_upstream_failure(anon_client):
    with respx.mock(base_url=settings.CATALOG_SERVICE_URL) as mock:
        mock.get("/internal/products/prod-x").mock(return_value=Response(500))
        response = await anon_client.get("/ai-discovery/products/prod-x/metadata")
    assert response.status_code == 502


@pytest.mark.asyncio
async def test_request_ai_export_requires_auth(anon_client):
    response = await anon_client.post("/ai-discovery/export")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_request_ai_export_queues_task(client, monkeypatch):
    class FakeAsyncResult:
        id = "task-ai-1"

    monkeypatch.setattr(
        "app.api.routes_ai_discovery.generate_ai_export_task.delay",
        lambda *a, **kw: FakeAsyncResult(),
    )
    response = await client.post("/ai-discovery/export")
    assert response.status_code == 202
    body = response.json()
    assert body["task_id"] == "task-ai-1"
    assert "batch_id" in body


@pytest.mark.asyncio
async def test_get_export_status_404_when_missing(anon_client):
    response = await anon_client.get("/ai-discovery/export/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ai_robots_directives_endpoint(anon_client):
    response = await anon_client.get("/ai-discovery/robots-ai.txt")
    assert response.status_code == 200
    assert "GPTBot" in response.text
    assert "Sitemap:" in response.text
