"""Item (SKU) catalog endpoints — raw ingredients, components, finished products."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, Roles, get_db, require_roles
from app.models.warehouse import Item
from app.schemas.warehouse import ItemCreate, ItemOut

router = APIRouter(prefix="/items", tags=["items"])


@router.post("", response_model=ItemOut, status_code=201)
async def create_item(
    payload: ItemCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER)),
):
    item = Item(**payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.get("", response_model=list[ItemOut])
async def list_items(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER, Roles.OPERATOR, Roles.VIEWER)),
):
    result = await db.scalars(select(Item))
    return list(result.all())


@router.get("/{item_id}", response_model=ItemOut)
async def get_item(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER, Roles.OPERATOR, Roles.VIEWER)),
):
    from fastapi import HTTPException, status
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item
