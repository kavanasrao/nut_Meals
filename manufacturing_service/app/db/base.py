"""
Base metadata registration for SQLAlchemy models.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# ==========================================================
# Manufacturing Models
# ==========================================================

from app.models.raw_material import RawMaterial
from app.models.bom import BOM
from app.models.bom_item import BOMItem
from app.models.production_batch import ProductionBatch
from app.models.batch_material import BatchMaterial
from app.models.lot_traceability import LotTraceability
from app.models.production_cost import ProductionCost
from app.models.manufacturing_audit import ManufacturingAudit


__all__ = [
    "Base",
    "RawMaterial",
    "BOM",
    "BOMItem",
    "ProductionBatch",
    "BatchMaterial",
    "LotTraceability",
    "ProductionCost",
    "ManufacturingAudit",
]