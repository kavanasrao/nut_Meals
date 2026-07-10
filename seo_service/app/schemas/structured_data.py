"""Pydantic schemas for schema.org JSON-LD structured data endpoints."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.structured_data import SchemaType


class StructuredDataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_type: str
    entity_id: str
    schema_type: SchemaType
    json_ld: dict
    schema_version: str
    is_valid: bool
    validation_errors: dict | None = None
    generated_at: datetime


class StructuredDataSyncRequest(BaseModel):
    entity_type: str
    entity_id: str
