"""Wishlist schemas."""
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WishlistItemCreate(BaseModel):
    product_id: UUID
    product_name: str = Field(..., max_length=255)
    unit_price: str = Field(..., max_length=32)
    image_url: Optional[str] = None


class WishlistItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    unit_price: str
    image_url: Optional[str]

    model_config = {"from_attributes": True}


class WishlistResponse(BaseModel):
    items: List[WishlistItemResponse]
    total: int
