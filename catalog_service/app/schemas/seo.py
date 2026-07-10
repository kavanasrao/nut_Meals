"""Pydantic schemas for SEO metadata."""
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SEOMetadataBase(BaseModel):
    meta_title: Optional[str] = Field(None, max_length=70)
    meta_description: Optional[str] = Field(None, max_length=320)
    meta_keywords: Optional[str] = Field(None, max_length=500)
    canonical_url: Optional[str] = Field(None, max_length=500)
    og_title: Optional[str] = Field(None, max_length=95)
    og_description: Optional[str] = Field(None, max_length=200)
    og_image_url: Optional[str] = Field(None, max_length=500)


class SEOMetadataUpsert(SEOMetadataBase):
    pass


class SEOMetadataRead(SEOMetadataBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_id: uuid.UUID
    structured_data: Optional[dict] = None
