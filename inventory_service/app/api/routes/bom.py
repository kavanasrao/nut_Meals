"""Bill of Materials endpoints: define recipes, version them, check availability."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, Roles, get_db, require_roles
from app.schemas.bom import BOMAvailabilityCheck, BOMAvailabilityResult, BOMCreate, BOMOut
from app.services import bom_service

router = APIRouter(prefix="/bom", tags=["bill-of-materials"])


@router.post("", response_model=BOMOut, status_code=201)
async def create_bom(
    payload: BOMCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER)),
):
    """Create a new (versioned) recipe for a product. Supersedes any prior
    active version for the same product without deleting history."""
    return await bom_service.create_bom(db, payload)


@router.get("/{bom_id}", response_model=BOMOut)
async def get_bom(
    bom_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER, Roles.OPERATOR, Roles.VIEWER)),
):
    return await bom_service.get_bom(db, bom_id)


@router.get("/product/{product_item_id}/active", response_model=BOMOut)
async def get_active_bom(
    product_item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER, Roles.OPERATOR, Roles.VIEWER)),
):
    return await bom_service.get_active_bom_for_product(db, product_item_id)


@router.get("/product/{product_item_id}/versions", response_model=list[BOMOut])
async def list_bom_versions(
    product_item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER, Roles.OPERATOR, Roles.VIEWER)),
):
    """Full version history of BOMs for a product."""
    return await bom_service.list_bom_versions(db, product_item_id)


@router.post("/{bom_id}/check-availability", response_model=BOMAvailabilityResult)
async def check_availability(
    bom_id: uuid.UUID,
    payload: BOMAvailabilityCheck,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER, Roles.OPERATOR, Roles.VIEWER)),
):
    """Validate component availability before committing to a production batch."""
    bom = await bom_service.get_bom(db, bom_id)
    return await bom_service.check_availability(db, bom, payload.warehouse_id, payload.planned_quantity)
