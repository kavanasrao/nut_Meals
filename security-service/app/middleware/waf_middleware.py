"""
ASGI middleware that inspects every inbound request against the active WAF
rule set before it reaches route handlers, using the same WafEngine that
backs the /waf/evaluate endpoint.

Mounted only in services that opt in (the Security Service itself, plus any
other FastAPI service that imports this middleware from a shared package in
practice). Body reads are capped at settings.WAF_MAX_BODY_BYTES to bound
memory/CPU cost per request.
"""
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.services.waf_engine import EvaluationInput, WafEngine

settings = get_settings()


class WafMiddleware(BaseHTTPMiddleware):
    """Blocks or logs requests that match an active WAF rule."""

    def __init__(self, app: ASGIApp, service_name: str = "security-service"):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.WAF_ENABLED:
            return await call_next(request)

        body_bytes = b""
        try:
            body_bytes = await request.body()
        except Exception:  # noqa: BLE001 - some requests (e.g. streaming) may not support .body()
            body_bytes = b""

        evaluation = EvaluationInput(
            method=request.method,
            path=request.url.path,
            query_string=str(request.url.query),
            headers=dict(request.headers),
            body_snippet=body_bytes[: settings.WAF_MAX_BODY_BYTES].decode("utf-8", errors="ignore"),
            source_ip=request.client.host if request.client else "unknown",
            service=self.service_name,
        )

        async with AsyncSessionLocal() as db:
            engine = WafEngine(db)
            allowed, matched_rule, fragment = await engine.evaluate(evaluation)

            if matched_rule is not None:
                await engine.record_incident(evaluation, matched_rule, fragment or "")

        if not allowed:
            return Response(
                content='{"detail":"Request blocked by WAF policy"}',
                status_code=403,
                media_type="application/json",
            )

        start = time.monotonic()
        response = await call_next(request)
        response.headers["X-Waf-Evaluated-Ms"] = str(round((time.monotonic() - start) * 1000, 2))
        return response
