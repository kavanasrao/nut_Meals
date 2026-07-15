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
"""
API Gateway — HTTP Reverse Proxy

Responsibilities
----------------
1. JWT Authentication
2. Rate Limiting
3. Request Forwarding
4. Response Streaming
5. Error Handling
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse

from app.core.auth import is_public_path, require_auth
from app.core.config import settings
from app.core.rate_limiter import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()

_http_client: httpx.AsyncClient | None = None


# ---------------------------------------------------------------------
# HTTP Client
# ---------------------------------------------------------------------
def get_http_client() -> httpx.AsyncClient:
    global _http_client

    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )

    return _http_client


async def close_http_client() -> None:
    global _http_client

    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()


# ---------------------------------------------------------------------
# Route Mapping
# ---------------------------------------------------------------------
ROUTES = {
    "/api/v1/orders": settings.ORDER_SERVICE_URL,
    "/api/v1/payments": settings.PAYMENT_SERVICE_URL,
    "/api/v1/delivery": settings.DELIVERY_SERVICE_URL,
    "/api/v1/notifications": settings.NOTIFICATION_SERVICE_URL,
    "/api/v1/users": settings.USER_SERVICE_URL,
    "/api/v1/meals": settings.MEAL_SERVICE_URL,
}


def resolve_upstream(path: str) -> str | None:
    for prefix, service in ROUTES.items():
        if path.startswith(prefix):
            return service
    return None


# ---------------------------------------------------------------------
# Reverse Proxy
# ---------------------------------------------------------------------
async def proxy_request(request: Request, upstream: str) -> Response:
    client = get_http_client()

    url = httpx.URL(f"{upstream}{request.url.path}")

    if request.url.query:
        url = url.copy_with(query=request.url.query.encode())

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower()
        not in {
            "host",
            "content-length",
            "connection",
            "transfer-encoding",
        }
    }

    body = await request.body()

    logger.info(
        "%s %s -> %s",
        request.method,
        request.url.path,
        upstream,
    )

    try:

        upstream_response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
        )

    except httpx.ConnectError:

        logger.exception("Unable to connect to %s", upstream)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable",
        )

    except httpx.TimeoutException:

        logger.exception("Timeout contacting %s", upstream)

        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Gateway timeout",
        )

    except httpx.HTTPError:

        logger.exception("Unexpected upstream error")

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Bad Gateway",
        )

    excluded_headers = {
        "content-length",
        "transfer-encoding",
        "connection",
        "keep-alive",
    }

    response_headers = {
        key: value
        for key, value in upstream_response.headers.items()
        if key.lower() not in excluded_headers
    }

    logger.info(
        "%s <- %s",
        upstream_response.status_code,
        upstream,
    )

    return StreamingResponse(
        upstream_response.aiter_bytes(),
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type"),
    )


# ---------------------------------------------------------------------
# Catch All Route
# ---------------------------------------------------------------------
@router.api_route(
    "/{full_path:path}",
    methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    include_in_schema=False,
)
async def gateway_proxy(
    request: Request,
    full_path: str,
) -> Response:

    path = request.url.path

    # Rate limiting
    await check_rate_limit(request)

    # Authentication
    if not is_public_path(path):
        require_auth(request)

    # Resolve destination service
    upstream = resolve_upstream(path)

    if upstream is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No service configured for {path}",
        )

    return await proxy_request(request, upstream)