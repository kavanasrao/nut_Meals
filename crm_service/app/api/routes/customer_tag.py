from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.repositories.customer_tag_repository import (
    CustomerTagRepository,
)
from app.schema.customer_tag import (
    CustomerTagCreate,
    CustomerTagResponse,
    CustomerTagUpdate,
)
from app.services.customer_tag_service import (
    CustomerTagService,
)

router = APIRouter(
    prefix="/customer-tags",
    tags=["Customer Tags"],
)


def get_service(
    db: AsyncSession = Depends(get_db),
) -> CustomerTagService:
    repository = CustomerTagRepository(db)
    return CustomerTagService(repository)


@router.post(
    "/",
    response_model=CustomerTagResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tag(
    payload: CustomerTagCreate,
    service: CustomerTagService = Depends(get_service),
):
    return await service.create_tag(payload)


@router.get(
    "/{tag_id}",
    response_model=CustomerTagResponse,
)
async def get_tag(
    tag_id: UUID,
    service: CustomerTagService = Depends(get_service),
):
    tag = await service.get_tag(tag_id)

    if tag is None:
        raise HTTPException(
            status_code=404,
            detail="Tag not found",
        )

    return tag


@router.get("/customer/{customer_id}")
async def get_customer_tags(
    customer_id: UUID,
    service: CustomerTagService = Depends(get_service),
):
    return await service.get_customer_tags(customer_id)


@router.put(
    "/{tag_id}",
    response_model=CustomerTagResponse,
)
async def update_tag(
    tag_id: UUID,
    payload: CustomerTagUpdate,
    service: CustomerTagService = Depends(get_service),
):
    tag = await service.update_tag(tag_id, payload)

    if tag is None:
        raise HTTPException(
            status_code=404,
            detail="Tag not found",
        )

    return tag


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: UUID,
    service: CustomerTagService = Depends(get_service),
):
    deleted = await service.delete_tag(tag_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Tag not found",
        )

    return {
        "message": "Tag deleted successfully",
    }