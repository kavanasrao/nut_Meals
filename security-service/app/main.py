"""
Security Service entrypoint.

Aggregates the WAF, audit, compliance, and RBAC routers behind shared
middleware (security headers + WAF inspection) and exposes health/readiness
endpoints for the container orchestrator.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import audit, compliance, rbac, waf
from app.config import get_settings
from app.middleware.auth_middleware import SecurityHeadersMiddleware
from app.middleware.waf_middleware import WafMiddleware

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)
logger = logging.getLogger("security-service")

app = FastAPI(
    title="nut_meals Security Service",
    description="Governance, monitoring, and compliance service: WAF, audit logs, "
    "compliance dashboards, and RBAC enforcement across nut_meals microservices.",
    version="1.0.0",
    docs_url="/docs" if settings.ENV != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
)
app.add_middleware(WafMiddleware, service_name=settings.SERVICE_NAME)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(waf.router)
app.include_router(audit.router)
app.include_router(compliance.router)
app.include_router(rbac.router)


@app.get("/health", tags=["ops"])
async def health():
    """Liveness probe -- returns 200 as long as the process is up."""
    return {"status": "ok", "service": settings.SERVICE_NAME}


@app.get("/ready", tags=["ops"])
async def ready():
    """Readiness probe -- verifies the DB is reachable before accepting traffic."""
    from sqlalchemy import text

    from app.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as exc:  # noqa: BLE001
        logger.error("Readiness check failed: %s", exc)
        return {"status": "not_ready", "error": str(exc)}
