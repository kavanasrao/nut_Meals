"""Business logic for warehouses, stock levels and transfers."""
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_movement
from app.models.warehouse import MovementType, StockLevel, StockTransfer, Warehouse
from app.schemas.warehouse import StockAdjustment, TransferCreate, WarehouseCreate, WarehouseUpdate


async def create_warehouse(db: AsyncSession, payload: WarehouseCreate) -> Warehouse:
    existing = await db.scalar(select(Warehouse).where(Warehouse.code == payload.code))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Warehouse code '{payload.code}' already exists")
    wh = Warehouse(**payload.model_dump())
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return wh


async def get_warehouse(db: AsyncSession, warehouse_id: uuid.UUID) -> Warehouse:
    wh = await db.get(Warehouse, warehouse_id)
    if not wh:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Warehouse not found")
    return wh


async def list_warehouses(db: AsyncSession, active_only: bool = False) -> list[Warehouse]:
    stmt = select(Warehouse)
    if active_only:
        stmt = stmt.where(Warehouse.is_active.is_(True))
    result = await db.scalars(stmt)
    return list(result.all())


async def update_warehouse(db: AsyncSession, warehouse_id: uuid.UUID, payload: WarehouseUpdate) -> Warehouse:
    wh = await get_warehouse(db, warehouse_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(wh, field, value)
    await db.commit()
    await db.refresh(wh)
    return wh


async def _get_or_create_stock_level(db: AsyncSession, warehouse_id: uuid.UUID, item_id: uuid.UUID) -> StockLevel:
    stmt = select(StockLevel).where(
        StockLevel.warehouse_id == warehouse_id, StockLevel.item_id == item_id
    ).with_for_update()
    stock = await db.scalar(stmt)
    if not stock:
        stock = StockLevel(warehouse_id=warehouse_id, item_id=item_id, quantity_on_hand=0, quantity_reserved=0)
        db.add(stock)
        await db.flush()
    return stock


async def list_stock_for_warehouse(db: AsyncSession, warehouse_id: uuid.UUID) -> list[StockLevel]:
    await get_warehouse(db, warehouse_id)
    result = await db.scalars(select(StockLevel).where(StockLevel.warehouse_id == warehouse_id))
    return list(result.all())


async def adjust_stock(
    db: AsyncSession, warehouse_id: uuid.UUID, payload: StockAdjustment, actor: str
) -> StockLevel:
    """Apply a manual inbound/outbound adjustment (e.g. receiving, cycle count correction)."""
    await get_warehouse(db, warehouse_id)
    stock = await _get_or_create_stock_level(db, warehouse_id, payload.item_id)

    new_on_hand = float(stock.quantity_on_hand) + payload.quantity_delta
    if new_on_hand < float(stock.quantity_reserved):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Adjustment would drop on-hand quantity below already-reserved quantity",
        )
    stock.quantity_on_hand = new_on_hand

    movement_type = MovementType.INBOUND if payload.quantity_delta >= 0 else MovementType.ADJUSTMENT
    await record_movement(
        db,
        item_id=payload.item_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
        quantity_delta=payload.quantity_delta,
        actor=actor,
        lot_number=payload.lot_number,
        notes=payload.notes,
    )
    await db.commit()
    await db.refresh(stock)
    return stock


async def transfer_stock(db: AsyncSession, payload: TransferCreate, actor: str) -> StockTransfer:
    """Move stock between warehouses atomically, logging both legs of the movement."""
    if payload.source_warehouse_id == payload.destination_warehouse_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Source and destination warehouses must differ")

    await get_warehouse(db, payload.source_warehouse_id)
    await get_warehouse(db, payload.destination_warehouse_id)

    source_stock = await _get_or_create_stock_level(db, payload.source_warehouse_id, payload.item_id)
    if source_stock.quantity_available < payload.quantity:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Insufficient available stock at source warehouse: "
            f"available={source_stock.quantity_available}, requested={payload.quantity}",
        )

    dest_stock = await _get_or_create_stock_level(db, payload.destination_warehouse_id, payload.item_id)

    source_stock.quantity_on_hand = float(source_stock.quantity_on_hand) - payload.quantity
    dest_stock.quantity_on_hand = float(dest_stock.quantity_on_hand) + payload.quantity

    transfer = StockTransfer(
        item_id=payload.item_id,
        source_warehouse_id=payload.source_warehouse_id,
        destination_warehouse_id=payload.destination_warehouse_id,
        quantity=payload.quantity,
        lot_number=payload.lot_number,
        initiated_by=actor,
        status="completed",
    )
    db.add(transfer)

    await record_movement(
        db, item_id=payload.item_id, warehouse_id=payload.source_warehouse_id,
        movement_type=MovementType.TRANSFER_OUT, quantity_delta=-payload.quantity,
        actor=actor, lot_number=payload.lot_number, reference_id=str(transfer.id),
    )
    await record_movement(
        db, item_id=payload.item_id, warehouse_id=payload.destination_warehouse_id,
        movement_type=MovementType.TRANSFER_IN, quantity_delta=payload.quantity,
        actor=actor, lot_number=payload.lot_number, reference_id=str(transfer.id),
    )

    await db.commit()
    await db.refresh(transfer)
    return transfer
