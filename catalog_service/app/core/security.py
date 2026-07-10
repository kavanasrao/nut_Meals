"""Security middleware: enforce HTTPS and set standard security headers.

In practice TLS termination happens at the load balancer / ingress, but this
middleware provides defense-in-depth by rejecting plaintext requests that
leak through (based on X-Forwarded-Proto) and setting hardening headers.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

settings = get_settings()


class HTTPSEnforcementMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if settings.force_https and settings.environment != "local":
            proto = request.headers.get("x-forwarded-proto", request.url.scheme)
            if proto != "https":
                return JSONResponse(
                    status_code=400, content={"detail": "HTTPS is required for this service"}
                )
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
