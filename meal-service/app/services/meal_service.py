"""Meal Service — business logic with Redis caching.

Caching strategy:
  - GET /meals (list)  → cache the full filtered result for MEAL_CACHE_TTL seconds
  - Any write (create/update/delete) → invalidate all meal list cache keys
  - Individual meal GET → not cached (list cache covers the common case)
"""
from __future__ import annotations

import json
import logging
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis
from app.models.meal import Meal
from app.schemas.meal import MealCreate, MealListResponse, MealOut, MealUpdate

logger = logging.getLogger(__name__)


def _cache_key(category: str | None, available_only: bool, limit: int, offset: int) -> str:
    return f"meals:list:cat={category or 'all'}:avail={available_only}:l={limit}:o={offset}"


class MealService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Queries ───────────────────────────────────────────────────────────────

    async def list_meals(
        self,
        *,
        category: str | None = None,
        available_only: bool = True,
        featured_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> MealListResponse:
        key = _cache_key(category, available_only, limit, offset)
        redis = await get_redis()

        # Cache hit
        cached = await redis.get(key)
        if cached:
            return MealListResponse.model_validate_json(cached)

        # Build query
        query = select(Meal)
        count_query = select(func.count()).select_from(Meal)

        if category:
            query = query.where(Meal.category == category)
            count_query = count_query.where(Meal.category == category)
        if available_only:
            query = query.where(Meal.is_available == True)
            count_query = count_query.where(Meal.is_available == True)
        if featured_only:
            query = query.where(Meal.is_featured == True)
            count_query = count_query.where(Meal.is_featured == True)

        total_r = await self.db.execute(count_query)
        total = total_r.scalar_one()

        query = query.order_by(Meal.sort_order.asc(), Meal.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        meals = list(result.scalars().all())

        response = MealListResponse(
            meals=[MealOut.model_validate(m) for m in meals],
            total=total,
            limit=limit,
            offset=offset,
        )

        # Cache result
        await redis.setex(key, settings.MEAL_CACHE_TTL, response.model_dump_json())
        return response

    async def get_meal(self, meal_id: str) -> Meal | None:
        try:
            mid = uuid.UUID(meal_id)
        except ValueError:
            return None
        result = await self.db.execute(select(Meal).where(Meal.id == mid))
        return result.scalar_one_or_none()

    # ── Mutations ─────────────────────────────────────────────────────────────

    async def create_meal(self, data: MealCreate) -> Meal:
        meal = Meal(
            id=uuid.uuid4(),
            **data.model_dump(),
        )
        self.db.add(meal)
        await self.db.commit()
        await self.db.refresh(meal)
        await self._bust_list_cache()
        logger.info("Meal created: %s (id=%s)", meal.name, meal.id)
        return meal

    async def update_meal(self, meal_id: str, data: MealUpdate) -> Meal | None:
        meal = await self.get_meal(meal_id)
        if not meal:
            return None
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(meal, field, value)
        await self.db.commit()
        await self.db.refresh(meal)
        await self._bust_list_cache()
        logger.info("Meal updated: %s", meal_id)
        return meal

    async def delete_meal(self, meal_id: str) -> bool:
        meal = await self.get_meal(meal_id)
        if not meal:
            return False
        await self.db.delete(meal)
        await self.db.commit()
        await self._bust_list_cache()
        logger.info("Meal deleted: %s", meal_id)
        return True

    async def toggle_availability(self, meal_id: str, available: bool) -> Meal | None:
        meal = await self.get_meal(meal_id)
        if not meal:
            return None
        meal.is_available = available
        await self.db.commit()
        await self.db.refresh(meal)
        await self._bust_list_cache()
        return meal

    # ── Cache management ──────────────────────────────────────────────────────

    async def _bust_list_cache(self) -> None:
        """Invalidate all meal list cache keys using scan+delete pattern."""
        redis = await get_redis()
        try:
            keys = []
            async for key in redis.scan_iter("meals:list:*"):
                keys.append(key)
            if keys:
                await redis.delete(*keys)
                logger.debug("Meal cache busted (%d keys)", len(keys))
        except Exception as exc:
            logger.warning("Could not bust meal cache: %s", exc)
