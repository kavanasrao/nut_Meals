"""
Baseline security headers + HTTPS enforcement middleware.

In production this service sits behind a load balancer that terminates TLS;
this middleware still enforces `X-Forwarded-Proto: https` and standard
hardening headers as defense-in-depth, and redirects/rejects plaintext HTTP
when ENFORCE_HTTPS is on.
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

settings = get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if settings.ENFORCE_HTTPS and settings.ENV != "local":
            forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
            if forwarded_proto != "https":
                return Response(
                    content='{"detail":"HTTPS required"}',
                    status_code=400,
                    media_type="application/json",
                )

        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response
