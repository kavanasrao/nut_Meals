from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.repositories.feedback_repository import FeedbackRepository
from app.schema.customer_feedback import (
    CustomerFeedbackCreate,
    CustomerFeedbackResponse,
    CustomerFeedbackUpdate,
)
from app.services.feedback_service import FeedbackService

router = APIRouter(
    prefix="/feedback",
    tags=["Customer Feedback"],
)


def get_service(
    db: AsyncSession = Depends(get_db),
) -> FeedbackService:
    repository = FeedbackRepository(db)
    return FeedbackService(repository)


@router.post(
    "/",
    response_model=CustomerFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_feedback(
    payload: CustomerFeedbackCreate,
    service: FeedbackService = Depends(get_service),
):
    return await service.create_feedback(payload)


@router.get(
    "/{feedback_id}",
    response_model=CustomerFeedbackResponse,
)
async def get_feedback(
    feedback_id: UUID,
    service: FeedbackService = Depends(get_service),
):
    feedback = await service.get_feedback(feedback_id)

    if feedback is None:
        raise HTTPException(
            status_code=404,
            detail="Feedback not found",
        )

    return feedback


@router.get("/customer/{customer_id}")
async def get_customer_feedback(
    customer_id: UUID,
    service: FeedbackService = Depends(get_service),
):
    return await service.get_customer_feedback(customer_id)


@router.get("/rating/{rating}")
async def get_feedback_by_rating(
    rating: int,
    service: FeedbackService = Depends(get_service),
):
    return await service.get_feedback_by_rating(rating)


@router.put(
    "/{feedback_id}",
    response_model=CustomerFeedbackResponse,
)
async def update_feedback(
    feedback_id: UUID,
    payload: CustomerFeedbackUpdate,
    service: FeedbackService = Depends(get_service),
):
    feedback = await service.update_feedback(
        feedback_id,
        payload,
    )

    if feedback is None:
        raise HTTPException(
            status_code=404,
            detail="Feedback not found",
        )

    return feedback


@router.patch("/{feedback_id}/resolve")
async def resolve_feedback(
    feedback_id: UUID,
    service: FeedbackService = Depends(get_service),
):
    feedback = await service.mark_resolved(feedback_id)

    if feedback is None:
        raise HTTPException(
            status_code=404,
            detail="Feedback not found",
        )

    return feedback


@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: UUID,
    service: FeedbackService = Depends(get_service),
):
    deleted = await service.delete_feedback(feedback_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Feedback not found",
        )

    return {
        "message": "Feedback deleted successfully"
    }