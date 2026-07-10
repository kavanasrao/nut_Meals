"""Tests for schema.org JSON-LD generation, validation, and API routes."""
import pytest

from app.models.structured_data import SchemaType
from app.services.structured_data_service import (
    StructuredDataService,
    build_blog_posting_json_ld,
    build_product_json_ld,
    validate_product_json_ld,
)

SAMPLE_PRODUCT = {
    "id": "prod-1",
    "name": "Roasted Almonds 500g",
    "slug": "roasted-almonds-500g",
    "sku": "ALM-500",
    "images": ["https://cdn.nutmeals.com/almonds.jpg"],
    "description": "Premium roasted almonds.",
    "brand": "nut_Meals",
    "price": 9.99,
    "currency": "USD",
    "in_stock": True,
}

SAMPLE_REVIEWS_SUMMARY = {"average_rating": 4.6, "review_count": 128}


def test_build_product_json_ld_includes_required_fields():
    json_ld = build_product_json_ld(SAMPLE_PRODUCT, SAMPLE_REVIEWS_SUMMARY)
    assert json_ld["@type"] == "Product"
    assert json_ld["name"] == "Roasted Almonds 500g"
    assert json_ld["offers"]["price"] == "9.99"
    assert json_ld["offers"]["availability"] == "https://schema.org/InStock"
    assert json_ld["aggregateRating"]["reviewCount"] == "128"


def test_build_product_json_ld_omits_rating_when_no_reviews():
    json_ld = build_product_json_ld(SAMPLE_PRODUCT, {"average_rating": 0, "review_count": 0})
    assert "aggregateRating" not in json_ld


def test_build_product_json_ld_out_of_stock():
    out_of_stock = {**SAMPLE_PRODUCT, "in_stock": False}
    json_ld = build_product_json_ld(out_of_stock, None)
    assert json_ld["offers"]["availability"] == "https://schema.org/OutOfStock"


def test_validate_product_json_ld_flags_missing_price():
    json_ld = build_product_json_ld(SAMPLE_PRODUCT, None)
    json_ld["offers"].pop("price")
    errors = validate_product_json_ld(json_ld)
    assert any("price" in e for e in errors)


def test_validate_product_json_ld_passes_for_complete_data():
    json_ld = build_product_json_ld(SAMPLE_PRODUCT, SAMPLE_REVIEWS_SUMMARY)
    errors = validate_product_json_ld(json_ld)
    assert errors == []


def test_build_blog_posting_json_ld():
    post = {
        "title": "5 Ways to Enjoy Almonds",
        "slug": "5-ways-to-enjoy-almonds",
        "cover_image": "https://cdn.nutmeals.com/blog/almonds.jpg",
        "author_name": "Jane Doe",
        "published_at": "2026-06-01T00:00:00Z",
    }
    json_ld = build_blog_posting_json_ld(post)
    assert json_ld["@type"] == "BlogPosting"
    assert json_ld["headline"] == post["title"]
    assert json_ld["author"]["name"] == "Jane Doe"


@pytest.mark.asyncio
async def test_upsert_record_creates_and_updates(db_session):
    service = StructuredDataService(db_session)
    json_ld = build_product_json_ld(SAMPLE_PRODUCT, None)
    record = await service.upsert_record(
        entity_type="product",
        entity_id="prod-1",
        schema_type=SchemaType.PRODUCT,
        json_ld=json_ld,
    )
    assert record.is_valid is True

    updated_json_ld = {**json_ld, "name": "Updated Name"}
    updated = await service.upsert_record(
        entity_type="product",
        entity_id="prod-1",
        schema_type=SchemaType.PRODUCT,
        json_ld=updated_json_ld,
        validation_errors=["Missing required field: image"],
    )
    assert updated.id == record.id
    assert updated.is_valid is False
    assert updated.validation_errors["errors"] == ["Missing required field: image"]


@pytest.mark.asyncio
async def test_get_product_structured_data_404_when_absent(anon_client):
    response = await anon_client.get("/structured-data/products/does-not-exist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_product_structured_data_returns_cached_record(anon_client, db_session):
    service = StructuredDataService(db_session)
    json_ld = build_product_json_ld(SAMPLE_PRODUCT, SAMPLE_REVIEWS_SUMMARY)
    await service.upsert_record(
        entity_type="product", entity_id="prod-1", schema_type=SchemaType.PRODUCT, json_ld=json_ld
    )
    await db_session.commit()

    response = await anon_client.get("/structured-data/products/prod-1")
    assert response.status_code == 200
    body = response.json()
    assert body["json_ld"]["@type"] == "Product"
    assert body["is_valid"] is True


@pytest.mark.asyncio
async def test_sync_structured_data_requires_auth(anon_client):
    response = await anon_client.post(
        "/structured-data/sync", json={"entity_type": "product", "entity_id": "prod-1"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sync_structured_data_queues_task(client, monkeypatch):
    class FakeAsyncResult:
        id = "task-999"

    monkeypatch.setattr(
        "app.api.routes_structured_data.sync_structured_data_task.delay",
        lambda *a, **kw: FakeAsyncResult(),
    )
    response = await client.post(
        "/structured-data/sync", json={"entity_type": "product", "entity_id": "prod-1"}
    )
    assert response.status_code == 202
    assert response.json()["task_id"] == "task-999"
