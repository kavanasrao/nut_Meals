"""
Unified Notification & Messaging Service — FastAPI entrypoint.
Runs as an independent microservice with its own DB, migrations,
Dockerfile, and CI/CD pipeline (see /docker-compose.yml, /.github).
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import audit, dlq, messages, notifications
from app.config import get_settings
from app.core.security import load_secrets_from_vault

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("notification-service")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_secrets_from_vault()
    logger.info("Notification & Messaging Service starting (env=%s)", settings.environment)
    yield
    logger.info("Notification & Messaging Service shutting down")


app = FastAPI(
    title="NutMeals Unified Notification & Messaging Service",
    version="1.0.0",
    lifespan=lifespan,
)

if settings.force_https and settings.is_production:
    app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*.nutmeals.com", "nutmeals.com"])


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Internal server error"})


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok", "service": "notification-messaging-service"}


@app.get("/", tags=["ops"])
async def root():
    return {"service": "NutMeals Notification & Messaging Service", "docs": "/docs"}


app.include_router(notifications.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(dlq.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
