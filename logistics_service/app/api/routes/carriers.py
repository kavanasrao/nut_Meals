"""Routes for carrier metadata and serviceability checks."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.security import Principal, enforce_https, require_roles
from app.models.carrier import Carrier
from app.schemas.carrier import CarrierOut, ServiceabilityRequest, ServiceabilityResponse
from app.services.serviceability import check_serviceability

router = APIRouter(prefix="/v1/carriers", tags=["carriers"], dependencies=[Depends(enforce_https)])


@router.get("", response_model=list[CarrierOut])
async def list_carriers(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles("logistics_admin", "logistics_ops", "logistics_viewer")),
):
    """List all onboarded carriers with their current rules-engine metadata."""
    result = await db.execute(select(Carrier))
    return result.scalars().all()


@router.post("/serviceability", response_model=ServiceabilityResponse)
async def serviceability_check(
    payload: ServiceabilityRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles("logistics_admin", "logistics_ops", "logistics_viewer")),
):
    """
    Check serviceability + get the rules-engine-recommended carrier for a
    given origin/destination/weight. Cached in Redis for
    `serviceability_cache_ttl` seconds.
    """
    return await check_serviceability(
        db, payload.origin_pincode, payload.destination_pincode, payload.weight_kg
    )
