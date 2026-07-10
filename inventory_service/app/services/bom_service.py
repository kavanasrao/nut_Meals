"""Business logic for Bill of Materials, including versioning and
pre-production stock availability validation."""
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bom import BillOfMaterial, BOMComponent
from app.models.warehouse import StockLevel
from app.schemas.bom import BOMAvailabilityResult, BOMCreate


async def create_bom(db: AsyncSession, payload: BOMCreate) -> BillOfMaterial:
    """Creates a new BOM version for a product. Any previously active BOM
    for the same product is deactivated (superseded), preserving history."""
    latest = await db.scalar(
        select(BillOfMaterial)
        .where(BillOfMaterial.product_item_id == payload.product_item_id)
        .order_by(BillOfMaterial.version.desc())
    )
    next_version = (latest.version + 1) if latest else 1

    if latest and latest.is_active:
        latest.is_active = False

    bom = BillOfMaterial(
        product_item_id=payload.product_item_id,
        version=next_version,
        yield_quantity=payload.yield_quantity,
        notes=payload.notes,
        is_active=True,
    )
    bom.components = [
        BOMComponent(component_item_id=c.component_item_id, quantity_required=c.quantity_required)
        for c in payload.components
    ]
    db.add(bom)
    await db.commit()
    await db.refresh(bom, attribute_names=["components"])
    return bom


async def get_bom(db: AsyncSession, bom_id: uuid.UUID) -> BillOfMaterial:
    stmt = select(BillOfMaterial).where(BillOfMaterial.id == bom_id).options(
        selectinload(BillOfMaterial.components)
    )
    bom = await db.scalar(stmt)
    if not bom:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "BOM not found")
    return bom


async def get_active_bom_for_product(db: AsyncSession, product_item_id: uuid.UUID) -> BillOfMaterial:
    stmt = select(BillOfMaterial).where(
        BillOfMaterial.product_item_id == product_item_id, BillOfMaterial.is_active.is_(True)
    ).options(selectinload(BillOfMaterial.components))
    bom = await db.scalar(stmt)
    if not bom:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active BOM found for this product")
    return bom


async def list_bom_versions(db: AsyncSession, product_item_id: uuid.UUID) -> list[BillOfMaterial]:
    stmt = select(BillOfMaterial).where(
        BillOfMaterial.product_item_id == product_item_id
    ).order_by(BillOfMaterial.version.desc()).options(selectinload(BillOfMaterial.components))
    result = await db.scalars(stmt)
    return list(result.all())


async def check_availability(
    db: AsyncSession, bom: BillOfMaterial, warehouse_id: uuid.UUID, planned_quantity: float
) -> BOMAvailabilityResult:
    """Validates that a warehouse holds enough available (non-reserved)
    stock of every component to run `planned_quantity` units through this
    BOM. Scales required quantities by planned_quantity / bom.yield_quantity.
    """
    scale = planned_quantity / float(bom.yield_quantity)
    shortfalls = []

    for component in bom.components:
        stock = await db.scalar(
            select(StockLevel).where(
                StockLevel.warehouse_id == warehouse_id,
                StockLevel.item_id == component.component_item_id,
            )
        )
        available = stock.quantity_available if stock else 0.0
        required = float(component.quantity_required) * scale
        if available < required:
            shortfalls.append({
                "component_item_id": str(component.component_item_id),
                "required": round(required, 3),
                "available": round(float(available), 3),
            })

    return BOMAvailabilityResult(is_available=len(shortfalls) == 0, shortfalls=shortfalls)
