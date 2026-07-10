"""
Thin async HTTP client for talking to the Catalog, Reviews, and Blog
microservices.

All cross-service calls are isolated here so retry/timeout/circuit
breaking policy lives in one place. In production, service-to-service
calls go over the internal mesh (mTLS terminated by the sidecar); this
client only needs to set the base URL and forward a trace header.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class UpstreamServiceError(Exception):
    """Raised when a call to an upstream microservice fails."""


class CatalogClient:
    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        self._base_url = base_url or settings.CATALOG_SERVICE_URL
        self._timeout = timeout or settings.CATALOG_SERVICE_TIMEOUT_SECONDS

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            logger.error("Upstream call failed: %s (%s)", url, exc)
            raise UpstreamServiceError(f"Failed to fetch {url}") from exc

    async def list_products(
        self, updated_after: str | None = None, page: int = 1, page_size: int = 500
    ) -> dict[str, Any]:
        """Paginated product listing, optionally filtered by updated_after (ISO 8601)."""
        params = {"page": page, "page_size": page_size}
        if updated_after:
            params["updated_after"] = updated_after
        return await self._get("/internal/products", params=params)

    async def get_product(self, product_id: str) -> dict[str, Any]:
        return await self._get(f"/internal/products/{product_id}")

    async def list_categories(self, page: int = 1, page_size: int = 500) -> dict[str, Any]:
        return await self._get(
            "/internal/categories", params={"page": page, "page_size": page_size}
        )

    async def get_product_reviews(self, product_id: str) -> dict[str, Any]:
        url = f"{settings.REVIEWS_SERVICE_URL}/internal/products/{product_id}/reviews"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            logger.error("Reviews fetch failed: %s (%s)", url, exc)
            raise UpstreamServiceError("Failed to fetch reviews") from exc

    async def list_blog_posts(self, page: int = 1, page_size: int = 500) -> dict[str, Any]:
        url = f"{settings.BLOG_SERVICE_URL}/internal/posts"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    url, params={"page": page, "page_size": page_size}
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            logger.error("Blog fetch failed: %s (%s)", url, exc)
            raise UpstreamServiceError("Failed to fetch blog posts") from exc

    async def list_catalog_redirects(self) -> list[dict[str, Any]]:
        """Fetch redirects owned by Catalog's own redirect manager (e.g. slug changes)."""
        data = await self._get("/internal/redirects")
        return data.get("redirects", [])


def get_catalog_client() -> CatalogClient:
    return CatalogClient()
