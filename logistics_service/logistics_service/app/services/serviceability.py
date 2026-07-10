"""
Serviceability checks and the carrier-selection rules engine.

Serviceability results are cached in Redis (keyed on origin/destination/
weight bucket) to avoid hammering carrier APIs. The rules engine scores each
serviceable carrier on a weighted combination of cost, speed and reliability,
configurable via `Settings.weight_*`.
"""
import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import CarrierAPIError
from app.adapters.registry import all_carrier_codes, get_adapter
from app.config import get_settings
from app.core.redis_client import get_redis
from app.models.carrier import Carrier, CarrierCode
from app.schemas.carrier import ServiceabilityOption, ServiceabilityResponse

logger = logging.getLogger(__name__)
settings = get_settings()


def _cache_key(origin: str, destination: str, weight_kg: float) -> str:
    weight_bucket = round(weight_kg, 1)
    return f"serviceability:{origin}:{destination}:{weight_bucket}"


def _score(cost: float, hours: float, reliability: float, max_cost: float, max_hours: float) -> float:
    """Higher score = better carrier choice. Cost/speed are inverted (lower is better)."""
    norm_cost = 1 - (cost / max_cost if max_cost else 0)
    norm_speed = 1 - (hours / max_hours if max_hours else 0)
    return (
        settings.weight_cost * norm_cost
        + settings.weight_speed * norm_speed
        + settings.weight_reliability * reliability
    )


async def check_serviceability(
    db: AsyncSession, origin_pincode: str, destination_pincode: str, weight_kg: float
) -> ServiceabilityResponse:
    """
    Check serviceability across all active carriers, using Redis cache first.
    Falls back to live carrier API calls on cache miss, with per-carrier
    failure isolation (one carrier failing doesn't block the others).
    """
    redis_client = get_redis()
    key = _cache_key(origin_pincode, destination_pincode, weight_kg)

    cached_raw = await redis_client.get(key)
    if cached_raw:
        payload = json.loads(cached_raw)
        return ServiceabilityResponse(**payload, cached=True)

    result = await db.execute(select(Carrier).where(Carrier.is_active.is_(True)))
    active_carriers = {c.code: c for c in result.scalars().all()}

    options: list[ServiceabilityOption] = []
    for code in all_carrier_codes():
        if code not in active_carriers:
            continue
        adapter = get_adapter(code)
        try:
            svc_result = await adapter.check_serviceability(origin_pincode, destination_pincode, weight_kg)
        except CarrierAPIError as exc:
            logger.warning("Serviceability check failed for %s: %s", code, exc)
            continue

        if not svc_result.serviceable:
            options.append(
                ServiceabilityOption(
                    carrier_code=code,
                    serviceable=False,
                    estimated_cost=0,
                    estimated_hours=0,
                    reliability_score=active_carriers[code].reliability_score,
                    score=0,
                )
            )
            continue

        options.append(
            ServiceabilityOption(
                carrier_code=code,
                serviceable=True,
                estimated_cost=svc_result.estimated_cost,
                estimated_hours=svc_result.estimated_hours,
                reliability_score=active_carriers[code].reliability_score,
                score=0,  # filled in below once we know max cost/hours
            )
        )

    serviceable_options = [o for o in options if o.serviceable]
    if serviceable_options:
        max_cost = max(o.estimated_cost for o in serviceable_options)
        max_hours = max(o.estimated_hours for o in serviceable_options)
        for o in serviceable_options:
            o.score = round(_score(o.estimated_cost, o.estimated_hours, o.reliability_score, max_cost, max_hours), 4)

    recommended = None
    if serviceable_options:
        recommended = max(serviceable_options, key=lambda o: o.score).carrier_code

    response = ServiceabilityResponse(
        origin_pincode=origin_pincode,
        destination_pincode=destination_pincode,
        recommended_carrier=recommended,
        options=options,
        cached=False,
    )

    await redis_client.set(
        key,
        json.dumps(
            {
                "origin_pincode": response.origin_pincode,
                "destination_pincode": response.destination_pincode,
                "recommended_carrier": response.recommended_carrier.value if response.recommended_carrier else None,
                "options": [o.model_dump(mode="json") for o in response.options],
            }
        ),
        ex=settings.serviceability_cache_ttl,
    )
    return response


async def get_carrier_priority_order(db: AsyncSession, origin: str, destination: str, weight_kg: float) -> list[CarrierCode]:
    """Return carriers ordered best-to-worst for allocation + fallback."""
    result = await check_serviceability(db, origin, destination, weight_kg)
    serviceable = sorted((o for o in result.options if o.serviceable), key=lambda o: o.score, reverse=True)
    return [o.carrier_code for o in serviceable]
