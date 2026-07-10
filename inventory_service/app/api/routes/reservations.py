"""Reservation endpoints consumed by the Orders service to hold stock
during checkout and confirm/release it based on payment outcome."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, Roles, get_db, require_roles
from app.schemas.reservation import ReservationCreate, ReservationOut
from app.services import reservation_service
from app.tasks.reservation_tasks import release_reservation_task

router = APIRouter(prefix="/reservations", tags=["reservations"])

# Orders service calls these using a service-to-service token with the
# ORDERS_SERVICE role; internal staff with MANAGER/ADMIN can also manage
# reservations directly (e.g. customer support overrides).
_RESERVATION_ROLES = (Roles.ADMIN, Roles.MANAGER, Roles.ORDERS_SERVICE)


@router.post("", response_model=ReservationOut, status_code=201)
async def create_reservation(
    payload: ReservationCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_RESERVATION_ROLES)),
):
    """Reserve stock for an order. Schedules an auto-release task at expiry."""
    reservation = await reservation_service.create_reservation(db, payload, actor=user.subject)
    ttl = payload.ttl_seconds
    release_reservation_task.apply_async(
        args=[str(reservation.id)],
        countdown=ttl if ttl else None,
        eta=None if ttl else reservation.expires_at,
    )
    return reservation


@router.get("/{reservation_id}", response_model=ReservationOut)
async def get_reservation(
    reservation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_RESERVATION_ROLES, Roles.VIEWER)),
):
    return await reservation_service.get_reservation(db, reservation_id)


@router.post("/{reservation_id}/confirm", response_model=ReservationOut)
async def confirm_reservation(
    reservation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_RESERVATION_ROLES)),
):
    """Called by Orders service when payment succeeds — permanently deducts stock."""
    return await reservation_service.confirm_reservation(db, reservation_id, actor=user.subject)


@router.post("/{reservation_id}/release", response_model=ReservationOut)
async def release_reservation(
    reservation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_RESERVATION_ROLES)),
):
    """Called by Orders service when payment fails or checkout is abandoned."""
    return await reservation_service.release_reservation(db, reservation_id, actor=user.subject, reason="payment_failed")
