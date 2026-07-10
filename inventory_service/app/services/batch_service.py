"""Business logic for production batches: creation, status transitions,
and inventory updates on completion."""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_movement
from app.models.batch import BatchStatus, ProductionBatch
from app.models.warehouse import MovementType, StockLevel
from app.schemas.batch import BatchCreate
from app.services.bom_service import check_availability, get_bom

VALID_TRANSITIONS: dict[BatchStatus, set[BatchStatus]] = {
    BatchStatus.PLANNED: {BatchStatus.IN_PROGRESS, BatchStatus.CANCELLED},
    BatchStatus.IN_PROGRESS: {BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.CANCELLED},
    BatchStatus.COMPLETED: set(),
    BatchStatus.CANCELLED: set(),
    BatchStatus.FAILED: set(),
}


def _generate_batch_number(product_sku: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"BATCH-{product_sku}-{ts}"


async def create_batch(db: AsyncSession, payload: BatchCreate, actor: str) -> ProductionBatch:
    """Creates a planned batch, first validating that component stock is
    available in the requested warehouse."""
    bom = await get_bom(db, payload.bom_id)
    availability = await check_availability(db, bom, payload.warehouse_id, payload.planned_quantity)
    if not availability.is_available:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"message": "Insufficient component stock for this batch", "shortfalls": availability.shortfalls},
        )

    batch = ProductionBatch(
        batch_number=_generate_batch_number(str(bom.product_item_id)[:8]),
        bom_id=payload.bom_id,
        warehouse_id=payload.warehouse_id,
        planned_quantity=payload.planned_quantity,
        lot_number=payload.lot_number,
        scheduled_start=payload.scheduled_start,
        status=BatchStatus.PLANNED,
        created_by=actor,
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return batch


async def get_batch(db: AsyncSession, batch_id: uuid.UUID) -> ProductionBatch:
    batch = await db.get(ProductionBatch, batch_id)
    if not batch:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Production batch not found")
    return batch


async def list_batches(db: AsyncSession, status_filter: BatchStatus | None = None) -> list[ProductionBatch]:
    stmt = select(ProductionBatch)
    if status_filter:
        stmt = stmt.where(ProductionBatch.status == status_filter)
    result = await db.scalars(stmt.order_by(ProductionBatch.created_at.desc()))
    return list(result.all())


async def start_batch(db: AsyncSession, batch_id: uuid.UUID, actor: str) -> ProductionBatch:
    """Transition PLANNED -> IN_PROGRESS and consume BOM component stock."""
    batch = await get_batch(db, batch_id)
    _assert_transition(batch.status, BatchStatus.IN_PROGRESS)

    bom = await get_bom(db, batch.bom_id)
    availability = await check_availability(db, bom, batch.warehouse_id, float(batch.planned_quantity))
    if not availability.is_available:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"message": "Component stock no longer available", "shortfalls": availability.shortfalls},
        )

    scale = float(batch.planned_quantity) / float(bom.yield_quantity)
    for component in bom.components:
        stock = await db.scalar(
            select(StockLevel).where(
                StockLevel.warehouse_id == batch.warehouse_id,
                StockLevel.item_id == component.component_item_id,
            ).with_for_update()
        )
        consume_qty = float(component.quantity_required) * scale
        stock.quantity_on_hand = float(stock.quantity_on_hand) - consume_qty
        await record_movement(
            db, item_id=component.component_item_id, warehouse_id=batch.warehouse_id,
            movement_type=MovementType.PRODUCTION_CONSUME, quantity_delta=-consume_qty,
            actor=actor, lot_number=batch.lot_number, reference_id=str(batch.id),
            notes=f"Consumed for batch {batch.batch_number}",
        )

    batch.status = BatchStatus.IN_PROGRESS
    batch.started_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(batch)
    return batch


async def complete_batch(
    db: AsyncSession, batch_id: uuid.UUID, actual_yield_quantity: float, actor: str
) -> ProductionBatch:
    """Transition IN_PROGRESS -> COMPLETED and credit finished-product stock."""
    batch = await get_batch(db, batch_id)
    _assert_transition(batch.status, BatchStatus.COMPLETED)

    bom = await get_bom(db, batch.bom_id)
    stock = await db.scalar(
        select(StockLevel).where(
            StockLevel.warehouse_id == batch.warehouse_id,
            StockLevel.item_id == bom.product_item_id,
        ).with_for_update()
    )
    if not stock:
        stock = StockLevel(warehouse_id=batch.warehouse_id, item_id=bom.product_item_id,
                            quantity_on_hand=0, quantity_reserved=0)
        db.add(stock)
        await db.flush()

    stock.quantity_on_hand = float(stock.quantity_on_hand) + actual_yield_quantity
    await record_movement(
        db, item_id=bom.product_item_id, warehouse_id=batch.warehouse_id,
        movement_type=MovementType.PRODUCTION_YIELD, quantity_delta=actual_yield_quantity,
        actor=actor, lot_number=batch.lot_number, reference_id=str(batch.id),
        notes=f"Yield from batch {batch.batch_number}",
    )

    batch.status = BatchStatus.COMPLETED
    batch.actual_yield_quantity = actual_yield_quantity
    batch.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(batch)
    return batch


async def cancel_or_fail_batch(
    db: AsyncSession, batch_id: uuid.UUID, new_status: BatchStatus, actor: str
) -> ProductionBatch:
    batch = await get_batch(db, batch_id)
    _assert_transition(batch.status, new_status)

    # If components were already consumed (batch was in progress), a FAILED
    # batch does not auto-return stock — that requires a manual adjustment
    # with proper documentation for compliance (spoiled/lost material).
    batch.status = new_status
    if new_status in (BatchStatus.CANCELLED, BatchStatus.FAILED):
        batch.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(batch)
    return batch


def _assert_transition(current: BatchStatus, target: BatchStatus) -> None:
    if target not in VALID_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid batch status transition: {current.value} -> {target.value}",
        )
