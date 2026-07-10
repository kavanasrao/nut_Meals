import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.carrier import CarrierCode


class CarrierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: CarrierCode
    name: str
    is_active: bool
    avg_cost_per_kg: float
    avg_delivery_hours: float
    reliability_score: float
    updated_at: datetime


class ServiceabilityRequest(BaseModel):
    origin_pincode: str
    destination_pincode: str
    weight_kg: float = 1.0
    cod_amount: float = 0.0


class ServiceabilityOption(BaseModel):
    carrier_code: CarrierCode
    serviceable: bool
    estimated_cost: float
    estimated_hours: float
    reliability_score: float
    score: float  # composite rules-engine score, higher is better


class ServiceabilityResponse(BaseModel):
    origin_pincode: str
    destination_pincode: str
    recommended_carrier: CarrierCode | None
    options: list[ServiceabilityOption]
    cached: bool
