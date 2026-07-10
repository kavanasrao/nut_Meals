"""
Business logic for AI-crawler discovery: metadata endpoints for
embeddings and bulk NDJSON catalog exports consumed by AI search /
RAG pipelines (our own, and well-behaved third-party AI crawlers that
respect `/ai-sitemap.xml` and `robots.txt` AI-agent directives).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_discovery import AiExportBatch, ExportStatus


def build_product_embedding_metadata(product: dict[str, Any]) -> dict[str, Any]:
    """
    Flattened, embedding-friendly representation of a product: plain
    text fields an embedding model can consume directly, plus
    structured facets for hybrid (vector + filter) search.
    """
    return {
        "id": product["id"],
        "type": "product",
        "title": product["name"],
        "text": " ".join(
            filter(
                None,
                [
                    product["name"],
                    product.get("description", ""),
                    product.get("category_name", ""),
                    " ".join(product.get("tags", [])),
                ],
            )
        ),
        "facets": {
            "brand": product.get("brand"),
            "category": product.get("category_name"),
            "price": product.get("price"),
            "currency": product.get("currency", "USD"),
            "in_stock": product.get("in_stock", True),
            "dietary_tags": product.get("dietary_tags", []),
        },
        "url": product.get("canonical_url"),
        "image": (product.get("images") or [None])[0],
        "updated_at": product.get("updated_at"),
    }


class AiDiscoveryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_batch(self, requested_by: str | None = None) -> AiExportBatch:
        batch = AiExportBatch(status=ExportStatus.PENDING, requested_by=requested_by)
        self.db.add(batch)
        await self.db.flush()
        return batch

    async def mark_running(self, batch_id: str) -> None:
        batch = await self.db.get(AiExportBatch, batch_id)
        if batch:
            batch.status = ExportStatus.RUNNING
            await self.db.flush()

    async def mark_complete(
        self, batch_id: str, *, file_path: str, record_count: int, ndjson_bytes: bytes
    ) -> None:
        batch = await self.db.get(AiExportBatch, batch_id)
        if batch:
            batch.status = ExportStatus.COMPLETE
            batch.file_path = file_path
            batch.record_count = record_count
            batch.checksum_sha256 = hashlib.sha256(ndjson_bytes).hexdigest()
            batch.completed_at = datetime.now(timezone.utc)
            await self.db.flush()

    async def mark_failed(self, batch_id: str, error_message: str) -> None:
        batch = await self.db.get(AiExportBatch, batch_id)
        if batch:
            batch.status = ExportStatus.FAILED
            batch.error_message = error_message
            await self.db.flush()

    async def get_batch(self, batch_id: str) -> AiExportBatch | None:
        return await self.db.get(AiExportBatch, batch_id)

    async def list_batches(self, limit: int = 20) -> list[AiExportBatch]:
        result = await self.db.execute(
            select(AiExportBatch).order_by(AiExportBatch.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    def to_ndjson(records: list[dict[str, Any]]) -> bytes:
        lines = [json.dumps(r, separators=(",", ":")) for r in records]
        return ("\n".join(lines) + "\n").encode("utf-8")
