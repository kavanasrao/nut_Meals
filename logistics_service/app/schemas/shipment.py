import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.shipment import ShipmentStatus, ShipmentType


class ShipmentCreate(BaseModel):
    order_id: uuid.UUID
    origin_pincode: str
    destination_pincode: str
    weight_kg: float = Field(gt=0)
    cod_amount: float = 0.0
    preferred_carrier: str | None = None


class ShipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    carrier_id: uuid.UUID
    carrier_awb: str | None
    shipment_type: ShipmentType
    status: ShipmentStatus
    origin_pincode: str
    destination_pincode: str
    weight_kg: float
    cod_amount: float
    created_at: datetime
    updated_at: datetime


class TrackingEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ShipmentStatus
    location: str | None
    remarks: str | None
    event_time: datetime


class TrackingResponse(BaseModel):
    shipment_id: uuid.UUID
    carrier_awb: str | None
    current_status: ShipmentStatus
    events: list[TrackingEventOut]


class ReversePickupCreate(BaseModel):
    original_shipment_id: uuid.UUID
    reason: str
    pickup_pincode: str
    weight_kg: float = Field(gt=0)
