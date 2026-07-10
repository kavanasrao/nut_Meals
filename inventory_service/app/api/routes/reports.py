"""Compliance reports: stock movement logs and lot traceability exports."""
import csv
import io
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, Roles, get_db, require_roles
from app.models.warehouse import StockMovementLog

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/movements")
async def list_movements(
    item_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    lot_number: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER, Roles.VIEWER)),
):
    """Query the immutable stock movement log — the audit trail backing
    lot traceability and compliance reporting."""
    stmt = select(StockMovementLog)
    if item_id:
        stmt = stmt.where(StockMovementLog.item_id == item_id)
    if warehouse_id:
        stmt = stmt.where(StockMovementLog.warehouse_id == warehouse_id)
    if lot_number:
        stmt = stmt.where(StockMovementLog.lot_number == lot_number)
    if start:
        stmt = stmt.where(StockMovementLog.timestamp >= start)
    if end:
        stmt = stmt.where(StockMovementLog.timestamp <= end)
    stmt = stmt.order_by(StockMovementLog.timestamp.desc()).limit(1000)

    result = await db.scalars(stmt)
    rows = result.all()
    return [
        {
            "id": str(r.id),
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "item_id": str(r.item_id),
            "warehouse_id": str(r.warehouse_id),
            "movement_type": r.movement_type.value,
            "quantity_delta": float(r.quantity_delta),
            "lot_number": r.lot_number,
            "reference_id": r.reference_id,
            "actor": r.actor,
            "notes": r.notes,
        }
        for r in rows
    ]


@router.get("/movements/export.csv")
async def export_movements_csv(
    lot_number: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER, Roles.VIEWER)),
):
    """Exportable CSV report for regulators/auditors, optionally filtered by lot."""
    stmt = select(StockMovementLog).order_by(StockMovementLog.timestamp.desc()).limit(5000)
    if lot_number:
        stmt = stmt.where(StockMovementLog.lot_number == lot_number)
    result = await db.scalars(stmt)
    rows = result.all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["timestamp", "item_id", "warehouse_id", "movement_type",
                      "quantity_delta", "lot_number", "reference_id", "actor", "notes"])
    for r in rows:
        writer.writerow([
            r.timestamp.isoformat() if r.timestamp else "", str(r.item_id), str(r.warehouse_id),
            r.movement_type.value, float(r.quantity_delta), r.lot_number or "",
            r.reference_id or "", r.actor, r.notes or "",
        ])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=stock_movements.csv"},
    )
