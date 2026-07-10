"""
Logistics Service entrypoint.

Wires together carrier integration, serviceability, shipment tracking,
returns, and compliance reporting routes into a single FastAPI app.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

from app.api.routes import carriers, reports, returns, tracking
from app.config import get_settings

settings = get_settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="nut_meals Logistics Service",
    description="Carrier integrations, serviceability, shipment tracking, and reverse logistics.",
    version="1.0.0",
)

if settings.enforce_https and settings.environment != "development":
    app.add_middleware(HTTPSRedirectMiddleware)

app.include_router(carriers.router)
app.include_router(tracking.router)
app.include_router(returns.router)
app.include_router(reports.router)


@app.get("/healthz", tags=["health"])
async def healthz():
    """Liveness/readiness probe used by Docker/Kubernetes."""
    return {"status": "ok", "service": settings.service_name, "environment": settings.environment}
