"""Business logic for reviews and moderation workflow."""
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.review import ProductRatingAggregate, Review, ReviewStatus
from app.schemas.review import ReviewCreate, ReviewModerate


async def create_review(
    db: AsyncSession, product_id: uuid.UUID, customer_id: uuid.UUID, payload: ReviewCreate
) -> Review:
    product_exists = await db.execute(select(Product.id).where(Product.id == product_id))
    if not product_exists.scalar_one_or_none():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")

    review = Review(
        product_id=product_id,
        customer_id=customer_id,
        status=ReviewStatus.PENDING,
        **payload.model_dump(),
    )
    db.add(review)
    await db.flush()
    await db.refresh(review)
    return review


async def get_review(db: AsyncSession, review_id: uuid.UUID) -> Review:
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Review not found")
    return review


async def list_reviews_for_product(
    db: AsyncSession, product_id: uuid.UUID, status_filter: ReviewStatus | None = None
) -> list[Review]:
    query = select(Review).where(Review.product_id == product_id)
    if status_filter:
        query = query.where(Review.status == status_filter)
    result = await db.execute(query.order_by(Review.created_at.desc()))
    return list(result.scalars().all())


async def list_pending_reviews(db: AsyncSession) -> list[Review]:
    result = await db.execute(
        select(Review).where(Review.status == ReviewStatus.PENDING).order_by(Review.created_at.asc())
    )
    return list(result.scalars().all())


async def moderate_review(
    db: AsyncSession, review_id: uuid.UUID, moderator_id: uuid.UUID, payload: ReviewModerate
) -> Review:
    review = await get_review(db, review_id)
    review.status = payload.status
    review.moderated_by = moderator_id
    review.moderation_notes = payload.moderation_notes
    await db.flush()

    await recompute_rating_aggregate(db, review.product_id)
    await db.refresh(review)
    return review


async def recompute_rating_aggregate(db: AsyncSession, product_id: uuid.UUID) -> ProductRatingAggregate:
    """Recompute the denormalized average rating / count from APPROVED reviews only.

    Called synchronously here for correctness, and also dispatched as a Celery
    task (see tasks/moderation_tasks.py) for cases where moderation happens
    via a batch/async path.
    """
    stats = await db.execute(
        select(func.avg(Review.rating), func.count(Review.id)).where(
            Review.product_id == product_id, Review.status == ReviewStatus.APPROVED
        )
    )
    avg_rating, count = stats.one()

    result = await db.execute(
        select(ProductRatingAggregate).where(ProductRatingAggregate.product_id == product_id)
    )
    aggregate = result.scalar_one_or_none()
    if aggregate is None:
        aggregate = ProductRatingAggregate(product_id=product_id)
        db.add(aggregate)

    aggregate.average_rating = round(float(avg_rating), 2) if avg_rating else 0.0
    aggregate.review_count = count or 0
    await db.flush()
    return aggregate
