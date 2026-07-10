"""Routes for reverse pickups (returns)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.security import Principal, enforce_https, require_roles
from app.models.shipment import Shipment
from app.schemas.shipment import ReversePickupCreate, ShipmentOut
from app.services.returns import ReversePickupError, create_reverse_pickup

router = APIRouter(prefix="/v1/returns", tags=["returns"], dependencies=[Depends(enforce_https)])


@router.post("", response_model=ShipmentOut, status_code=status.HTTP_201_CREATED)
async def create_return(
    payload: ReversePickupCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles("logistics_admin", "logistics_ops")),
):
    """Book a reverse pickup against the carrier used for the original shipment."""
    original = await db.get(Shipment, payload.original_shipment_id)
    if original is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original shipment not found")

    try:
        reverse_shipment = await create_reverse_pickup(
            db,
            original_shipment=original,
            reason=payload.reason,
            pickup_pincode=payload.pickup_pincode,
            weight_kg=payload.weight_kg,
            actor=principal.user_id,
        )
    except ReversePickupError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    await db.commit()
    return reverse_shipment
