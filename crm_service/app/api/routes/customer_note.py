from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.repositories.customer_note_repository import (
    CustomerNoteRepository,
)
from app.schema.customer_note import (
    CustomerNoteCreate,
    CustomerNoteResponse,
    CustomerNoteUpdate,
)
from app.services.customer_note_service import (
    CustomerNoteService,
)

router = APIRouter(
    prefix="/customer-notes",
    tags=["Customer Notes"],
)


def get_service(
    db: AsyncSession = Depends(get_db),
) -> CustomerNoteService:
    repository = CustomerNoteRepository(db)
    return CustomerNoteService(repository)


@router.post(
    "/",
    response_model=CustomerNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_note(
    payload: CustomerNoteCreate,
    service: CustomerNoteService = Depends(get_service),
):
    return await service.create_note(payload)


@router.get(
    "/{note_id}",
    response_model=CustomerNoteResponse,
)
async def get_note(
    note_id: UUID,
    service: CustomerNoteService = Depends(get_service),
):
    note = await service.get_note(note_id)

    if note is None:
        raise HTTPException(
            status_code=404,
            detail="Customer note not found",
        )

    return note


@router.get("/customer/{customer_id}")
async def get_customer_notes(
    customer_id: UUID,
    service: CustomerNoteService = Depends(get_service),
):
    return await service.get_customer_notes(customer_id)


@router.get("/customer/{customer_id}/internal")
async def get_internal_notes(
    customer_id: UUID,
    service: CustomerNoteService = Depends(get_service),
):
    return await service.get_internal_notes(customer_id)


@router.put(
    "/{note_id}",
    response_model=CustomerNoteResponse,
)
async def update_note(
    note_id: UUID,
    payload: CustomerNoteUpdate,
    service: CustomerNoteService = Depends(get_service),
):
    note = await service.update_note(
        note_id,
        payload,
    )

    if note is None:
        raise HTTPException(
            status_code=404,
            detail="Customer note not found",
        )

    return note


@router.delete("/{note_id}")
async def delete_note(
    note_id: UUID,
    service: CustomerNoteService = Depends(get_service),
):
    deleted = await service.delete_note(note_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Customer note not found",
        )

    return {
        "message": "Customer note deleted successfully",
    }