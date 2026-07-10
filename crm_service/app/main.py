from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.analytics import router as analytics_router
from app.api.routes.campaign import router as campaign_router
from app.api.routes.customer_address import (
    router as customer_address_router,
)
from app.api.routes.customer_interaction import (
    router as customer_interaction_router,
)
from app.api.routes.customer_note import (
    router as customer_note_router,
)
from app.api.routes.customer_preference import (
    router as customer_preference_router,
)
from app.api.routes.customer_profile import (
    router as customer_profile_router,
)
from app.api.routes.customer_segment import (
    router as customer_segment_router,
)
from app.api.routes.customer_tag import (
    router as customer_tag_router,
)
from app.api.routes.customer_timeline import (
    router as customer_timeline_router,
)
from app.api.routes.feedback import router as feedback_router
from app.api.routes.loyalty import router as loyalty_router
from app.api.routes.reports import router as reports_router
from app.api.routes.support_ticket import (
    router as support_ticket_router,
)
from app.core.config import settings
from app.core.logging import setup_logging


setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 CRM Service Started")
    yield
    print("🛑 CRM Service Stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# -----------------------
# Customer Management
# -----------------------
app.include_router(customer_profile_router)
app.include_router(customer_address_router)
app.include_router(customer_tag_router)
app.include_router(customer_segment_router)
app.include_router(customer_timeline_router)
app.include_router(customer_note_router)
app.include_router(customer_preference_router)
app.include_router(customer_interaction_router)

# -----------------------
# Support
# -----------------------
app.include_router(support_ticket_router)

# -----------------------
# Campaigns
# -----------------------
app.include_router(campaign_router)

# -----------------------
# Loyalty
# -----------------------
app.include_router(loyalty_router)

# -----------------------
# Feedback
# -----------------------
app.include_router(feedback_router)

# -----------------------
# Analytics & Reports
# -----------------------
app.include_router(analytics_router)
app.include_router(reports_router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }