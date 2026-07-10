"""Pydantic schemas for WAF rules and incidents."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.waf import WafAction, WafRuleType


class WafRuleBase(BaseModel):
    name: str = Field(..., max_length=128)
    rule_type: WafRuleType
    pattern: str = Field(..., description="Regex, CIDR, or JSON config depending on rule_type")
    action: WafAction = WafAction.BLOCK
    severity: int = Field(5, ge=1, le=10)
    applies_to_service: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class WafRuleCreate(WafRuleBase):
    pass


class WafRuleUpdate(BaseModel):
    pattern: Optional[str] = None
    action: Optional[WafAction] = None
    severity: Optional[int] = Field(None, ge=1, le=10)
    is_active: Optional[bool] = None
    description: Optional[str] = None


class WafRuleOut(WafRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WafIncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rule_name: str
    rule_type: WafRuleType
    action_taken: WafAction
    source_ip: str
    method: str
    path: str
    service: str
    matched_fragment: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime


class WafEvaluateRequest(BaseModel):
    """Payload other services can POST to have the Security Service evaluate
    a request out-of-band (in addition to the inline middleware)."""

    method: str
    path: str
    query_string: Optional[str] = ""
    headers: dict[str, str] = Field(default_factory=dict)
    body_snippet: Optional[str] = ""
    source_ip: str
    service: str
    user_id: Optional[str] = None


class WafEvaluateResponse(BaseModel):
    allowed: bool
    matched_rule: Optional[WafRuleOut] = None
    incident: Optional[WafIncidentOut] = None
