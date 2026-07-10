"""Structured audit logging for compliance-sensitive inventory actions.

Every stock-affecting operation must call `record_movement`, which both
writes an immutable StockMovementLog row (source of truth for lot
traceability/exports) and emits a structured log line for centralized log
aggregation (e.g. shipped to a SIEM).
"""
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.warehouse import MovementType, StockMovementLog

logger = logging.getLogger("inventory.audit")
logging.basicConfig(level=logging.INFO)


async def record_movement(
    db: AsyncSession,
    *,
    item_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    movement_type: MovementType,
    quantity_delta: float,
    actor: str,
    lot_number: str | None = None,
    reference_id: str | None = None,
    notes: str | None = None,
) -> StockMovementLog:
    log = StockMovementLog(
        item_id=item_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
        quantity_delta=quantity_delta,
        lot_number=lot_number,
        reference_id=reference_id,
        actor=actor,
        notes=notes,
    )
    db.add(log)
    await db.flush()
    logger.info(
        "stock_movement",
        extra={
            "item_id": str(item_id),
            "warehouse_id": str(warehouse_id),
            "movement_type": movement_type.value,
            "quantity_delta": float(quantity_delta),
            "lot_number": lot_number,
            "reference_id": reference_id,
            "actor": actor,
        },
    )
    return log
