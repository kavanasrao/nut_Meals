"""Meal Service — REST API routes.

GET  /api/v1/meals                   — list meals (cached, public)
GET  /api/v1/meals/featured          — featured meals (cached)
GET  /api/v1/meals/{meal_id}         — single meal
POST /api/v1/meals                   — create meal (admin)
PUT  /api/v1/meals/{meal_id}         — full update (admin)
PATCH /api/v1/meals/{meal_id}        — partial update (admin)
DELETE /api/v1/meals/{meal_id}       — delete meal (admin)
PATCH /api/v1/meals/{meal_id}/availability — toggle availability (admin)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.meal import MealCreate, MealListResponse, MealOut, MealUpdate
from app.services.meal_service import MealService

router = APIRouter(prefix="/meals", tags=["meals"])


@router.get("/", response_model=MealListResponse, summary="List meals (public, cached)")
async def list_meals(
    category: Optional[str] = Query(default=None),
    available_only: bool = Query(default=True),
    featured_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> MealListResponse:
    svc = MealService(db)
    return await svc.list_meals(
        category=category,
        available_only=available_only,
        featured_only=featured_only,
        limit=limit,
        offset=offset,
    )


@router.get("/featured", response_model=MealListResponse, summary="Featured meals")
async def featured_meals(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> MealListResponse:
    svc = MealService(db)
    return await svc.list_meals(available_only=True, featured_only=True, limit=limit)


@router.get("/{meal_id}", response_model=MealOut, summary="Get a single meal")
async def get_meal(meal_id: str, db: AsyncSession = Depends(get_db)) -> MealOut:
    svc = MealService(db)
    meal = await svc.get_meal(meal_id)
    if not meal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")
    return MealOut.model_validate(meal)


@router.post(
    "/",
    response_model=MealOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a meal (admin)",
)
async def create_meal(body: MealCreate, db: AsyncSession = Depends(get_db)) -> MealOut:
    svc = MealService(db)
    meal = await svc.create_meal(body)
    return MealOut.model_validate(meal)


@router.put("/{meal_id}", response_model=MealOut, summary="Full update of a meal (admin)")
async def replace_meal(
    meal_id: str,
    body: MealCreate,
    db: AsyncSession = Depends(get_db),
) -> MealOut:
    svc = MealService(db)
    meal = await svc.update_meal(
        meal_id,
        MealUpdate(**body.model_dump()),
    )
    if not meal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")
    return MealOut.model_validate(meal)


@router.patch("/{meal_id}", response_model=MealOut, summary="Partial update of a meal (admin)")
async def update_meal(
    meal_id: str,
    body: MealUpdate,
    db: AsyncSession = Depends(get_db),
) -> MealOut:
    svc = MealService(db)
    meal = await svc.update_meal(meal_id, body)
    if not meal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")
    return MealOut.model_validate(meal)


@router.delete(
    "/{meal_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a meal (admin)",
)
async def delete_meal(meal_id: str, db: AsyncSession = Depends(get_db)) -> None:
    svc = MealService(db)
    deleted = await svc.delete_meal(meal_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")


@router.patch(
    "/{meal_id}/availability",
    response_model=MealOut,
    summary="Toggle meal availability (admin)",
)
async def set_availability(
    meal_id: str,
    available: bool = Query(..., description="true to enable, false to disable"),
    db: AsyncSession = Depends(get_db),
) -> MealOut:
    svc = MealService(db)
    meal = await svc.toggle_availability(meal_id, available)
    if not meal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")
    return MealOut.model_validate(meal)
