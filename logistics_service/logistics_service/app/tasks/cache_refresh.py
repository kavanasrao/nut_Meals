"""
Celery task that proactively refreshes the Redis serviceability cache for
high-traffic origin/destination pairs (e.g. top warehouse pincodes to top
customer delivery pincodes), so customer-facing serviceability checks hit
warm cache instead of live carrier APIs during peak traffic.
"""
import asyncio
import logging

from app.core.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.services.serviceability import check_serviceability

logger = logging.getLogger(__name__)

# In production this would be sourced from analytics (top N warehouse ->
# delivery pincode pairs by order volume, refreshed daily). Kept as a small
# static seed list here to keep the task self-contained.
_HIGH_TRAFFIC_ROUTES: list[tuple[str, str, float]] = [
    ("560001", "110001", 1.0),
    ("560001", "400001", 1.0),
    ("560001", "600001", 1.0),
    ("560001", "700001", 1.0),
]


@celery_app.task(name="app.tasks.cache_refresh.refresh_serviceability_cache")
def refresh_serviceability_cache() -> dict:
    return asyncio.run(_refresh_serviceability_cache_async())


async def _refresh_serviceability_cache_async() -> dict:
    refreshed = 0
    async with AsyncSessionLocal() as db:
        for origin, destination, weight in _HIGH_TRAFFIC_ROUTES:
            try:
                await check_serviceability(db, origin, destination, weight)
                refreshed += 1
            except Exception:
                logger.exception("Failed to refresh serviceability cache for %s -> %s", origin, destination)

    logger.info("Refreshed serviceability cache for %d routes", refreshed)
    return {"refreshed": refreshed}
