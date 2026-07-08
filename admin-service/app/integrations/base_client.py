"""Base HTTP client for all downstream service integrations.

Every service client inherits from this class, which provides:
  - Shared async httpx client (connection pooling)
  - Automatic internal service token injection
  - Consistent error handling and logging
  - Timeout configuration from settings
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ServiceUnavailableError(Exception):
    """Raised when a downstream service cannot be reached."""


class DownstreamError(Exception):
    """Raised when a downstream service returns a 4xx/5xx response."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Downstream error {status_code}: {detail}")


class BaseServiceClient:
    """
    Async HTTP client base class.

    Subclasses set `base_url` to their service URL.
    All requests automatically include the internal service auth header.
    """

    base_url: str = ""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=settings.DOWNSTREAM_TIMEOUT,
                headers={
                    "X-Internal-Token": settings.INTERNAL_SERVICE_TOKEN,
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        """Execute an HTTP request and return parsed JSON."""
        client = self._get_client()
        try:
            response = await client.request(method, path, params=params, json=json)
        except httpx.ConnectError as exc:
            logger.error("Cannot connect to %s%s: %s", self.base_url, path, exc)
            raise ServiceUnavailableError(f"Service at {self.base_url} is unavailable") from exc
        except httpx.TimeoutException as exc:
            logger.error("Timeout calling %s%s: %s", self.base_url, path, exc)
            raise ServiceUnavailableError(f"Service at {self.base_url} timed out") from exc

        if response.is_error:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            logger.warning("Downstream %s error %d from %s%s", method, response.status_code, self.base_url, path)
            raise DownstreamError(response.status_code, detail)

        # 204 No Content
        if response.status_code == 204 or not response.content:
            return None

        return response.json()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: Any = None) -> Any:
        return await self._request("POST", path, json=json)

    async def put(self, path: str, json: Any = None) -> Any:
        return await self._request("PUT", path, json=json)

    async def patch(self, path: str, json: Any = None) -> Any:
        return await self._request("PATCH", path, json=json)

    async def delete(self, path: str) -> Any:
        return await self._request("DELETE", path)

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
