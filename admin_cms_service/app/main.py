"""
FastAPI application entrypoint for the Admin CMS Service.

This service runs independently from admin-service, with its own
Dockerfile, database, migrations, and CI/CD pipeline (microservices
architecture). It provides finance dashboards, returns management,
content/blog management, and analytics for administrators.
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routes import analytics, content, finance, returns
from app.services.base_client import ServiceUnavailableError

settings = get_settings()

logging.basicConfig(level=logging.INFO if not settings.debug else logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Admin CMS Service",
    description=(
        "Dashboards, content management, and analytics for nut_Meals administrators. "
        "Extends admin-service functionality; runs as an independent microservice."
    ),
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

# --- Security middleware ---
if settings.force_https and settings.environment == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[] if settings.environment == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(ServiceUnavailableError)
async def service_unavailable_handler(request: Request, exc: ServiceUnavailableError) -> JSONResponse:
    """Return a clean 502 when an upstream microservice call fails, instead of a raw 500."""
    logger.error("Upstream service call failed: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": "An upstream service is currently unavailable. Please try again shortly."},
    )


@app.get("/healthz", tags=["health"])
async def healthz() -> dict:
    """Liveness/readiness probe for Kubernetes/Docker health checks."""
    return {"status": "ok", "service": settings.service_name}


app.include_router(finance.router)
app.include_router(returns.router)
app.include_router(content.router)
app.include_router(analytics.router)
