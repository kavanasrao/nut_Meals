import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_read, require_write
from app.core.security import CurrentUser
from app.database import get_db
from app.schemas.grn import GRNCreate, GRNRead
from app.services.grn_service import GRNService

router = APIRouter(prefix="/grn", tags=["Goods Receipt Notes"])


@router.post("", response_model=GRNRead, status_code=status.HTTP_201_CREATED)
async def create_grn(
    payload: GRNCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_write),
):
    return await GRNService(db).create_grn(payload, received_by=user.id)


@router.get("/{grn_id}", response_model=GRNRead)
async def get_grn(
    grn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_read),
):
    return await GRNService(db).get_grn(grn_id)


@router.get("/by-po/{po_id}", response_model=list[GRNRead])
async def list_grns_for_po(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_read),
):
    return await GRNService(db).list_grns_for_po(po_id)
