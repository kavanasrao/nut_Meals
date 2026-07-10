from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime
    is_active: bool
    is_deleted: bool