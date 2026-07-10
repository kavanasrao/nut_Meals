"""Pydantic schemas for reviews and moderation."""
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.review import ReviewStatus


class ReviewCreate(BaseModel):
    customer_name: str = Field(..., max_length=150)
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    body: Optional[str] = Field(None, max_length=5000)


class ReviewModerate(BaseModel):
    status: ReviewStatus
    moderation_notes: Optional[str] = Field(None, max_length=500)


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_id: uuid.UUID
    customer_name: str
    rating: int
    title: Optional[str]
    body: Optional[str]
    status: ReviewStatus


class RatingAggregateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: uuid.UUID
    average_rating: float
    review_count: int
