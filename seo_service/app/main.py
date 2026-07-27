"""
nut_Meals SEO Service — FastAPI application entrypoint.

Responsibilities:
- Dynamic sitemaps
- Schema.org structured data
- AI crawler discovery readiness
- Redirect/canonical management
- Blog CMS
- Recipe Content
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse

from app.api.routes_ai_discovery import router as ai_discovery_router
from app.api.blog_category import router as blog_category_router
from app.api.blog_post import router as blog_post_router
from app.api.routes_recipe import router as recipe_router
from app.api.routes_redirects import router as redirects_router
from app.api.routes_sitemap import router as sitemap_router
from app.api.routes_structured_data import router as structured_data_router

from app.config import get_settings
from app.services.catalog_client import UpstreamServiceError

settings = get_settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seo_service")

app = FastAPI(
    title="nut_Meals SEO Service",
    description=(
        "Dynamic sitemaps, schema.org structured data, "
        "AI discovery readiness, redirect/canonical management, "
        "Blog CMS, and Recipe Content for nut_Meals."
    ),
    version="1.0.0",
)

# ==========================================================
# Middleware
# ==========================================================

# HTTPS enforcement in production
if settings.HTTPS_ONLY and settings.ENV == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.PUBLIC_BASE_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=[
        "Authorization",
        "Content-Type",
    ],
)

# ==========================================================
# API Routes
# ==========================================================

app.include_router(sitemap_router)

app.include_router(structured_data_router)

app.include_router(ai_discovery_router)

app.include_router(redirects_router)

app.include_router(blog_category_router)

app.include_router(blog_post_router)

app.include_router(recipe_router)

# ==========================================================
# Exception Handlers
# ==========================================================

@app.exception_handler(UpstreamServiceError)
async def upstream_error_handler(
    request: Request,
    exc: UpstreamServiceError,
) -> JSONResponse:
    logger.error(
        "Upstream service error on %s: %s",
        request.url.path,
        exc,
    )

    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "detail": (
                "An upstream service is temporarily unavailable."
            )
        },
    )

# ==========================================================
# Health Check
# ==========================================================

@app.get("/healthz", tags=["Health"])
async def health_check() -> dict:
    """
    Liveness/readiness probe for orchestration
    (Kubernetes, Docker, ECS, etc.).
    """
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
    }