"""Routes for creating shipments and fetching tracking status."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.core.security import Principal, enforce_https, require_roles
from app.models.carrier import CarrierCode
from app.models.shipment import Shipment
from app.schemas.shipment import ShipmentCreate, ShipmentOut, TrackingResponse
from app.services.allocation import NoServiceableCarrierError, allocate_and_book_shipment
from app.services.tracking import sync_shipment_tracking

router = APIRouter(prefix="/v1/shipments", tags=["shipments"], dependencies=[Depends(enforce_https)])


@router.post("", response_model=ShipmentOut, status_code=status.HTTP_201_CREATED)
async def create_shipment(
    payload: ShipmentCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles("logistics_admin", "logistics_ops")),
):
    """
    Book a forward shipment. Selects the best carrier via the rules engine
    (or the caller's `preferred_carrier` if serviceable), with automatic
    fallback to the next-ranked carrier if booking fails.
    """
    preferred = CarrierCode(payload.preferred_carrier) if payload.preferred_carrier else None
    try:
        shipment = await allocate_and_book_shipment(
            db,
            order_id=payload.order_id,
            origin_pincode=payload.origin_pincode,
            destination_pincode=payload.destination_pincode,
            weight_kg=payload.weight_kg,
            cod_amount=payload.cod_amount,
            actor=principal.user_id,
            preferred_carrier=preferred,
        )
    except NoServiceableCarrierError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    await db.commit()
    return shipment


@router.get("/{shipment_id}", response_model=ShipmentOut)
async def get_shipment(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles("logistics_admin", "logistics_ops", "logistics_viewer")),
):
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    return shipment


@router.get("/{shipment_id}/tracking", response_model=TrackingResponse)
async def get_tracking(
    shipment_id: uuid.UUID,
    force_refresh: bool = False,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles("logistics_admin", "logistics_ops", "logistics_viewer")),
):
    """
    Return tracking history for a shipment. If `force_refresh=true`, pulls
    fresh checkpoints from the carrier before responding (otherwise relies on
    the periodic Celery sync to keep events current).
    """
    result = await db.execute(
        select(Shipment).options(selectinload(Shipment.tracking_events)).where(Shipment.id == shipment_id)
    )
    shipment = result.scalar_one_or_none()
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")

    if force_refresh:
        shipment = await sync_shipment_tracking(db, shipment, actor=principal.user_id)
        await db.commit()
        result = await db.execute(
            select(Shipment)
            .options(selectinload(Shipment.tracking_events))
            .where(Shipment.id == shipment_id)
            .execution_options(populate_existing=True)
        )
        shipment = result.scalar_one()

    return TrackingResponse(
        shipment_id=shipment.id,
        carrier_awb=shipment.carrier_awb,
        current_status=shipment.status,
        events=shipment.tracking_events,
    )
