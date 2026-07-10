"""Warehouse, stock level, and transfer endpoints."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, Roles, get_db, require_roles
from app.schemas.warehouse import (
    StockAdjustment, StockLevelOut, TransferCreate, TransferOut,
    WarehouseCreate, WarehouseOut, WarehouseUpdate,
)
from app.services import warehouse_service

router = APIRouter(prefix="/warehouses", tags=["warehouses"])


@router.post("", response_model=WarehouseOut, status_code=201)
async def create_warehouse(
    payload: WarehouseCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER)),
):
    """Define a new warehouse with location and capacity."""
    return await warehouse_service.create_warehouse(db, payload)


@router.get("", response_model=list[WarehouseOut])
async def list_warehouses(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER, Roles.OPERATOR, Roles.VIEWER)),
):
    return await warehouse_service.list_warehouses(db, active_only=active_only)


@router.get("/{warehouse_id}", response_model=WarehouseOut)
async def get_warehouse(
    warehouse_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER, Roles.OPERATOR, Roles.VIEWER)),
):
    return await warehouse_service.get_warehouse(db, warehouse_id)


@router.patch("/{warehouse_id}", response_model=WarehouseOut)
async def update_warehouse(
    warehouse_id: uuid.UUID,
    payload: WarehouseUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER)),
):
    return await warehouse_service.update_warehouse(db, warehouse_id, payload)


@router.get("/{warehouse_id}/stock", response_model=list[StockLevelOut])
async def list_stock(
    warehouse_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER, Roles.OPERATOR, Roles.VIEWER)),
):
    """Track stock levels for every item held in this warehouse."""
    return await warehouse_service.list_stock_for_warehouse(db, warehouse_id)


@router.post("/{warehouse_id}/stock/adjust", response_model=StockLevelOut)
async def adjust_stock(
    warehouse_id: uuid.UUID,
    payload: StockAdjustment,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER, Roles.OPERATOR)),
):
    """Manually adjust stock (receiving, cycle-count correction, spoilage)."""
    return await warehouse_service.adjust_stock(db, warehouse_id, payload, actor=user.subject)


@router.post("/transfers", response_model=TransferOut, status_code=201)
async def create_transfer(
    payload: TransferCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER, Roles.OPERATOR)),
):
    """Transfer stock from one warehouse to another."""
    return await warehouse_service.transfer_stock(db, payload, actor=user.subject)
