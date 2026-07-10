"""
Base async HTTP client for calling other internal microservices, with
shared-secret service-to-service authentication, timeouts, and retries.
"""
import logging
from typing import Any, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ServiceUnavailableError(Exception):
    """Raised when an upstream internal service call ultimately fails."""


class BaseServiceClient:
    """
    Thin wrapper around httpx.AsyncClient for calling a specific upstream
    service. Subclasses set `base_url` and add typed convenience methods.
    """

    def __init__(self, base_url: str, timeout: float = 5.0, max_retries: int = 2):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.internal_service_token}",
            "X-Service-Name": settings.service_name,
        }

    async def _request(
        self, method: str, path: str, *, params: Optional[dict] = None, json: Optional[dict] = None
    ) -> Any:
        url = f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await client.request(
                        method, url, params=params, json=json, headers=self._headers()
                    )
                    response.raise_for_status()
                    return response.json()
                except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                    last_exc = exc
                    logger.warning(
                        "Call to %s failed (attempt %s/%s): %s", url, attempt, self.max_retries, exc
                    )

        raise ServiceUnavailableError(f"Failed to call {url} after {self.max_retries} attempts") from last_exc

    async def get(self, path: str, params: Optional[dict] = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: Optional[dict] = None) -> Any:
        return await self._request("POST", path, json=json)
