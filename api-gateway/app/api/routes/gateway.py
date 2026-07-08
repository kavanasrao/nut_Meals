"""API Gateway — HTTP reverse proxy routes.

All client requests arrive here.  The gateway:
  1. Validates the JWT (via middleware).
  2. Checks rate limits.
  3. Forwards the request to the correct downstream service.
  4. Streams the response back to the client.

Route → Service mapping:
  /api/v1/orders/*      → order-service
  /api/v1/payments/*    → payment-service   (webhook is public)
  /api/v1/delivery/*    → delivery-service
  /api/v1/notifications/* → notification-service (internal)
"""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse

from app.core.auth import is_public_path, require_auth
from app.core.config import settings
from app.core.rate_limiter import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()

# Shared async HTTP client (connection pooling)
_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    return _http_client


async def close_http_client() -> None:
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()


# ── Routing table ────────────────────────────────────────────────────────────
def _resolve_upstream(path: str) -> str | None:
    """Return the upstream base URL for the given path prefix."""
    routes = [
        ("/api/v1/orders", settings.ORDER_SERVICE_URL),
        ("/api/v1/payments", settings.PAYMENT_SERVICE_URL),
        ("/api/v1/delivery", settings.DELIVERY_SERVICE_URL),
        ("/api/v1/notifications", settings.NOTIFICATION_SERVICE_URL),
        ("/api/v1/users", settings.USER_SERVICE_URL),
        ("/api/v1/meals", settings.MEAL_SERVICE_URL),
    ]
    for prefix, upstream in routes:
        if path.startswith(prefix):
            return upstream
    return None


# ── Proxy helper ─────────────────────────────────────────────────────────────
async def _proxy(request: Request, upstream: str) -> Response:
    """Forward the request to the upstream service and return its response."""
    client = get_http_client()
    url = httpx.URL(f"{upstream}{request.url.path}")
    if request.url.query:
        url = url.copy_with(query=request.url.query.encode())

    # Forward all headers except host
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }

    try:
        body = await request.body()
        upstream_response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
        )
    except httpx.ConnectError:
        logger.error("Cannot connect to upstream: %s", upstream)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Upstream service unavailable: {upstream}",
        )
    except httpx.TimeoutException:
        logger.error("Timeout connecting to upstream: %s", upstream)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Upstream service timed out",
        )

    # Stream response back
    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=dict(upstream_response.headers),
        media_type=upstream_response.headers.get("content-type"),
    )


# ── Catch-all route ───────────────────────────────────────────────────────────
@router.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    include_in_schema=False,
)
async def gateway_proxy(
    request: Request,
    full_path: str,
) -> Response:
    path = request.url.path

    # ── Rate limit (all routes) ───────────────────────────────────────
    await check_rate_limit(request)

    # ── Auth check (skip public paths) ───────────────────────────────
    if not is_public_path(path):
        require_auth(request)

    # ── Route to upstream ─────────────────────────────────────────────
    upstream = _resolve_upstream(path)
    if upstream is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No upstream service found for path: {path}",
        )

    return await _proxy(request, upstream)
