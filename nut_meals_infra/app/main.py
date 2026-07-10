"""
nut_Meals Deployment/Infra Service
Production-ready FastAPI service for infrastructure automation, backups, and recovery.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.api.v1.router import api_router
from app.core.redis import init_redis, close_redis

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("Starting nut_Meals Infra Service", version=settings.APP_VERSION)
    await init_redis()
    yield
    logger.info("Shutting down nut_Meals Infra Service")
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(
        title="nut_Meals Infra Service",
        description="Infrastructure automation, backups, and recovery for nut_Meals platform",
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

    # Routes
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "healthy", "service": "infra", "version": settings.APP_VERSION}

    return app


configure_logging()
app = create_app()
