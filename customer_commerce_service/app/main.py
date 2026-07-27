"""FastAPI application factory for Customer & Commerce Service."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s [%s]", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)
    yield
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Nut Meals — Customer & Commerce Service",
        version=settings.APP_VERSION,
        description=(
            "Manages carts, wishlists, coupon engine, saved addresses, "
            "and GST-compliant invoice generation."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if settings.ENVIRONMENT == "production":
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

    # ── Custom validation error handler ────────────────────────────────────────
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors(), "body": exc.body},
        )

    # ── Health check ───────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health():
        return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}

    # ── Routers ────────────────────────────────────────────────────────────────
    app.include_router(api_router)

    return app


app = create_app()
