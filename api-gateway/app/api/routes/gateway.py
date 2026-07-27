"""
API Gateway — HTTP Reverse Proxy
=================================

Single entry point into the NutMeals microservices ecosystem.

Responsibilities
----------------
• JWT Authentication (async-safe)
• Redis Rate Limiting
• Request Routing  (longest-prefix match)
• Streaming Reverse Proxy
• Response Forwarding
• Correlation / Request-ID propagation
• Error Handling
• Startup / Shutdown lifecycle

Route Mapping
-------------
/api/v1/auth             -> security-service
/api/v1/users            -> user-service
/api/v1/catalog          -> catalog-service
/api/v1/meals            -> meal-service
/api/v1/customer         -> customer-commerce-service
/api/v1/inventory        -> inventory-service
/api/v1/orders           -> order-service
/api/v1/payments         -> payment-service
/api/v1/manufacturing    -> manufacturing-service
/api/v1/procurement      -> procurement-service
/api/v1/logistics        -> logistics-service
/api/v1/crm              -> crm-service
/api/v1/notifications    -> notification-service
/api/v1/seo              -> seo-service
/api/v1/finance          -> finance-service
/api/v1/admin            -> admin-service
/api/v1/admin-cms        -> admin-cms-service
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx

from fastapi import (
    APIRouter,
    FastAPI,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import StreamingResponse
from app.core.auth import get_current_user, is_public_path
from app.core.config import get_settings
from app.core.rate_limiter import check_rate_limit

logger = logging.getLogger(__name__)

settings = get_settings()

# ==============================================================
# Hop-by-hop headers (single source of truth)
# Used when preparing outbound requests AND filtering responses.
# ==============================================================

HOP_BY_HOP_HEADERS: frozenset[str] = frozenset(
    {
        "connection",
        "content-length",      # httpx sets this correctly
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
)

# ==============================================================
# Route Mapping
# ==============================================================

ROUTES: dict[str, str] = {
    "/api/v1/auth":          settings.SECURITY_SERVICE_URL,
    "/api/v1/users":         settings.USER_SERVICE_URL,
    "/api/v1/catalog":       settings.CATALOG_SERVICE_URL,
    "/api/v1/meals":         settings.MEAL_SERVICE_URL,
    "/api/v1/customer":      settings.CUSTOMER_COMMERCE_SERVICE_URL,
    "/api/v1/inventory":     settings.INVENTORY_SERVICE_URL,
    "/api/v1/orders":        settings.ORDER_SERVICE_URL,
    "/api/v1/payments":      settings.PAYMENT_SERVICE_URL,
    "/api/v1/manufacturing": settings.MANUFACTURING_SERVICE_URL,
    "/api/v1/procurement":   settings.PROCUREMENT_SERVICE_URL,
    "/api/v1/logistics":     settings.LOGISTICS_SERVICE_URL,
    "/api/v1/crm":           settings.CRM_SERVICE_URL,
    "/api/v1/notifications": settings.NOTIFICATION_SERVICE_URL,
    "/api/v1/seo":           settings.SEO_SERVICE_URL,
    "/api/v1/finance":       settings.FINANCE_SERVICE_URL,
    "/api/v1/admin":         settings.ADMIN_SERVICE_URL,
    "/api/v1/admin-cms":     settings.ADMIN_CMS_SERVICE_URL,
}

# Pre-sort once at startup (longest prefix first) so matching is O(n)
# with no re-sorting on every request.
_SORTED_ROUTES: list[tuple[str, str]] = sorted(
    ROUTES.items(), key=lambda kv: len(kv[0]), reverse=True
)

# ==============================================================
# HTTP Client — managed via FastAPI lifespan
# ==============================================================

# Stored at module level so the router functions can reach it,
# but ONLY populated inside the lifespan context (never at import time).
_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """
    Return the shared HTTP client.
    Raises RuntimeError if called before lifespan startup.
    """
    if _http_client is None:
        raise RuntimeError(
            "HTTP client has not been initialised. "
            "Did you forget to register the lifespan context?"
        )
    return _http_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    FastAPI lifespan context.

    Initialises the shared HTTP client on startup and
    cleanly closes it on shutdown — even if an exception occurs.

    Usage:
        app = FastAPI(lifespan=lifespan)
    """
    global _http_client

    logger.info("Gateway startup: initialising HTTP client.")

    _http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=5.0,
            read=60.0,
            write=60.0,
            pool=10.0,
        ),
        limits=httpx.Limits(
            max_connections=200,
            max_keepalive_connections=50,
            keepalive_expiry=30.0,
        ),
        follow_redirects=True,
        # Enable HTTP/2 for multiplexing to high-throughput services
        http2=True,
    )

    logger.info("Gateway startup: HTTP client ready.")

    yield  # <-- application runs here

    logger.info("Gateway shutdown: closing HTTP client.")
    await _http_client.aclose()
    _http_client = None
    logger.info("Gateway shutdown: HTTP client closed.")


# ==============================================================
# Router
# NOTE: Gateway-specific endpoints (/gateway/*) are registered
# BEFORE the catch-all proxy route so FastAPI matches them first.
# ==============================================================

router = APIRouter(prefix="", tags=["Gateway"])


# ==============================================================
# Gateway Endpoints  (must be declared before the catch-all)
# ==============================================================

@router.get("/gateway/health", include_in_schema=True)
async def gateway_health() -> dict[str, object]:
    """Public health check — always visible in docs."""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "environment": settings.ENVIRONMENT,
        "routes": len(ROUTES),
    }


@router.get("/gateway/routes", include_in_schema=False)
async def gateway_routes() -> dict[str, object]:
    """
    List all configured routes.
    Hidden from Swagger; enable behind an internal auth check
    rather than relying on include_in_schema alone.
    """
    return {
        "service": settings.SERVICE_NAME,
        "total_routes": len(ROUTES),
        "routes": ROUTES,
    }


@router.get("/gateway/info", include_in_schema=False)
async def gateway_info() -> dict[str, object]:
    """Runtime configuration summary (internal only)."""
    return {
        "service": settings.SERVICE_NAME,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "rate_limit_window": settings.RATE_LIMIT_WINDOW_SECONDS,
        "rate_limit_requests": settings.RATE_LIMIT_MAX_REQUESTS,
    }


# ==============================================================
# Helper Functions
# ==============================================================

def _resolve_route(path: str) -> tuple[str, str]:
    """
    Return (service_url, matched_prefix) for the given path.

    Uses pre-sorted list (_SORTED_ROUTES) — longest prefix wins.

    Raises:
        HTTPException(404) if no route matches.
    """
    for prefix, service_url in _SORTED_ROUTES:
        if path.startswith(prefix):
            return service_url, prefix

    logger.warning("No downstream service found for path: %s", path)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No service registered for '{path}'.",
    )


def _build_target_url(service_url: str, request_path: str) -> str:
    """
    Concatenate the service base URL with the full request path.

    Example:
        service_url   = "http://order-service:8000"
        request_path  = "/api/v1/orders/15"
        result        = "http://order-service:8000/api/v1/orders/15"
    """
    return service_url.rstrip("/") + "/" + request_path.lstrip("/")


def _prepare_forward_headers(
    request: Request,
    request_id: str,
) -> dict[str, str]:
    """
    Build the header dict to send to the downstream service.

    • Strips all hop-by-hop headers.
    • Injects gateway-specific forwarding headers.
    • Propagates or generates a correlation X-Request-ID.
    """
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
        and key.lower() != "host"   # always replaced by httpx
    }

    # Gateway identity
    headers["X-Gateway"] = settings.SERVICE_NAME
    headers["X-Internal-Service-Token"] = settings.INTERNAL_SERVICE_TOKEN

    # Forwarding metadata
    headers["X-Forwarded-Proto"] = request.url.scheme
    headers["X-Forwarded-Host"] = request.url.hostname or ""
    headers["X-Forwarded-For"] = (
        request.client.host if request.client else "unknown"
    )

    # Correlation ID — use the one the client sent or generate a new one
    headers["X-Request-ID"] = request_id

    return headers


def _filter_response_headers(
    upstream_headers: httpx.Headers,
) -> dict[str, str]:
    """
    Strip hop-by-hop headers from the upstream response
    before forwarding to the client.

    Content-Length is excluded because the body may be
    chunked/compressed differently by the gateway.
    """
    return {
        key: value
        for key, value in upstream_headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }


# ==============================================================
# Streaming Reverse Proxy  (catch-all — declared LAST)
# ==============================================================

@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_request(path: str, request: Request) -> Response:
    """
    Catch-all reverse proxy.

    Pipeline:
      1. Resolve / generate correlation request ID
      2. Authenticate (skip public paths)
      3. Rate-limit
      4. Resolve downstream service
      5. Forward request (streaming)
      6. Stream response back to client
    """

    request_path = "/" + path

    # ----------------------------------------------------------
    # 1. Correlation ID
    # ----------------------------------------------------------

    request_id: str = (
        request.headers.get("X-Request-ID") or str(uuid.uuid4())
    )

    # ----------------------------------------------------------
    # 2. Authentication
    # ----------------------------------------------------------

    if not is_public_path(request_path):
        # get_current_user must be an async function.
        # If it only decodes a local JWT (no I/O), it can remain sync
        # but should be wrapped: await run_in_executor(None, get_current_user, request)
        await get_current_user(request)

    # ----------------------------------------------------------
    # 3. Rate Limiting
    # ----------------------------------------------------------

    await check_rate_limit(request)

    # ----------------------------------------------------------
    # 4. Resolve Downstream Service
    # ----------------------------------------------------------

    service_url, _ = _resolve_route(request_path)
    target_url = _build_target_url(service_url, request_path)

    logger.info(
        "[%s] %s %s -> %s",
        request_id,
        request.method,
        request_path,
        target_url,
    )

    # ----------------------------------------------------------
    # 5. Forward Request (streaming body)
    # ----------------------------------------------------------

    headers = _prepare_forward_headers(request, request_id)

    try:
        upstream_request = get_http_client().build_request(
            method=request.method,
            url=target_url,
            params=request.query_params.multi_items(),  # preserves multi-value params
            headers=headers,
            content=request.stream(),                   # stream body, no full buffering
        )

        upstream_response = await get_http_client().send(
            upstream_request,
            stream=True,   # stream the response back
        )

    except httpx.ConnectError as exc:
        logger.error(
            "[%s] Connection refused: %s — %s",
            request_id, target_url, exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Downstream service unavailable.",
        ) from exc

    except httpx.TimeoutException as exc:
        logger.error(
            "[%s] Gateway timeout: %s — %s",
            request_id, target_url, exc,
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Gateway timeout.",
        ) from exc

    except httpx.HTTPError as exc:
        logger.exception(
            "[%s] Unexpected HTTP error forwarding to %s",
            request_id, target_url,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Bad Gateway.",
        ) from exc

    # ----------------------------------------------------------
    # 6. Stream Response to Client
    # ----------------------------------------------------------

    response_headers = _filter_response_headers(upstream_response.headers)
    response_headers["X-Request-ID"] = request_id  # echo back for tracing

    logger.info(
        "[%s] <- %s %s HTTP %d",
        request_id,
        request.method,
        request_path,
        upstream_response.status_code,
    )

    return StreamingResponse(
        content=upstream_response.aiter_bytes(chunk_size=8192),
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type"),
        background=None,
    )


# ==============================================================
# Module Exports
# ==============================================================

__all__ = [
    "router",
    "lifespan",
    "ROUTES",
]


# ==============================================================
# Startup Logging
# ==============================================================

logger.info("=" * 60)
logger.info("NutMeals API Gateway loaded")
logger.info("Environment : %s", settings.ENVIRONMENT)
logger.info("Service     : %s", settings.SERVICE_NAME)
logger.info("Routes      : %d", len(ROUTES))
logger.info("=" * 60)
for prefix, service in sorted(ROUTES.items()):
    logger.info("  %-28s -> %s", prefix, service)

