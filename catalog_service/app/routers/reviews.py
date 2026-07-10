"""Review submission + moderation workflow endpoints."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.core.rbac import CurrentUser, Role, require_roles
from app.database import get_db
from app.models.review import ReviewStatus
from app.schemas.review import RatingAggregateRead, ReviewCreate, ReviewModerate, ReviewRead
from app.services import review_service
from app.tasks.moderation_tasks import recompute_rating_aggregate_task

router = APIRouter(tags=["reviews"])


@router.post("/api/v1/products/{product_id}/reviews", response_model=ReviewRead, status_code=201)
async def submit_review(
    product_id: uuid.UUID,
    payload: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.CUSTOMER, Role.VIEWER)),
):
    """Customer submits a review. It enters PENDING status and awaits moderation."""
    review = await review_service.create_review(db, product_id, uuid.UUID(user.id), payload)
    await db.commit()
    return review


@router.get("/api/v1/products/{product_id}/reviews", response_model=list[ReviewRead])
async def list_product_reviews(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Public endpoint: returns only APPROVED reviews for storefront display."""
    return await review_service.list_reviews_for_product(db, product_id, status_filter=ReviewStatus.APPROVED)


@router.get("/api/v1/products/{product_id}/reviews/rating", response_model=RatingAggregateRead)
async def get_product_rating(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Public endpoint returning the denormalized aggregate rating for a product.
    The aggregate table is the source of truth; it is recomputed synchronously
    on every moderation decision and asynchronously via a Celery task."""
    from app.services.product_service import get_rating_aggregate

    return await get_rating_aggregate(db, product_id)


@router.get("/api/v1/reviews/pending", response_model=list[ReviewRead])
async def list_pending_reviews(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.MODERATOR)),
):
    """Moderator queue: all reviews awaiting approval/rejection."""
    return await review_service.list_pending_reviews(db)


@router.post("/api/v1/reviews/{review_id}/moderate", response_model=ReviewRead)
async def moderate_review(
    review_id: uuid.UUID,
    payload: ReviewModerate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.MODERATOR)),
):
    """Approve or reject a review. Triggers async aggregate rating recompute."""
    review = await review_service.moderate_review(db, review_id, uuid.UUID(user.id), payload)
    await write_audit_log(
        db,
        actor_id=user.id,
        actor_role=user.role.value,
        action=f"review.{payload.status.value}",
        resource_type="review",
        resource_id=str(review_id),
    )
    await db.commit()
    # Dispatch async recompute as well, for eventual-consistency dashboards / caches
    recompute_rating_aggregate_task.delay(str(review.product_id))
    return review
