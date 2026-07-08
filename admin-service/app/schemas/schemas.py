"""All Pydantic request/response schemas for the Admin Service.

Grouped by domain in a single file for easy cross-referencing.
Split into separate files if this grows beyond ~400 lines.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.models import AdminRole


# ============================================================================
# Auth
# ============================================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: AdminRole


class RefreshRequest(BaseModel):
    refresh_token: str


# ============================================================================
# Admin Users
# ============================================================================

class AdminUserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: AdminRole = AdminRole.ADMIN


class AdminUserOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: AdminRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[AdminRole] = None
    is_active: Optional[bool] = None


# ============================================================================
# System Config
# ============================================================================

class ConfigEntry(BaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1)
    description: Optional[str] = None


class ConfigUpdate(BaseModel):
    value: str = Field(..., min_length=1)
    description: Optional[str] = None


class ConfigOut(BaseModel):
    id: UUID
    key: str
    value: str
    description: Optional[str] = None
    updated_by: Optional[str] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# Audit Logs
# ============================================================================

class AuditLogOut(BaseModel):
    id: UUID
    admin_id: str
    admin_email: str
    admin_role: str
    action: str
    resource: str
    resource_id: Optional[str] = None
    http_method: Optional[str] = None
    http_path: Optional[str] = None
    ip_address: Optional[str] = None
    request_payload: Optional[dict[str, Any]] = None
    response_status: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogFilter(BaseModel):
    admin_email: Optional[str] = None
    action: Optional[str] = None
    resource: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


# ============================================================================
# User Management (proxied from User Service)
# ============================================================================

class UserOut(BaseModel):
    """Shape returned by User Service — accept any valid structure."""
    id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    created_at: Optional[str] = None

    model_config = {"extra": "allow"}


class UserListResponse(BaseModel):
    users: list[dict[str, Any]]
    total: int


# ============================================================================
# Order Management (proxied from Order Service)
# ============================================================================

class OrderStatusUpdate(BaseModel):
    status: str = Field(
        ...,
        pattern=r"^(pending|confirmed|preparing|out_for_delivery|delivered|cancelled)$",
    )


class OrderListResponse(BaseModel):
    orders: list[dict[str, Any]]
    total: int


# ============================================================================
# Meal / Menu Management (proxied from Meal Service)
# ============================================================================

class MealCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    price: Decimal = Field(..., gt=Decimal("0"))
    category: str = Field(..., min_length=1, max_length=100)
    is_available: bool = True
    image_url: Optional[str] = None
    tags: Optional[list[str]] = None


class MealUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=Decimal("0"))
    category: Optional[str] = None
    is_available: Optional[bool] = None
    image_url: Optional[str] = None
    tags: Optional[list[str]] = None


# ============================================================================
# Delivery Management
# ============================================================================

class DeliveryOptionCreate(BaseModel):
    type: str = Field(..., pattern=r"^(pickup|home_delivery|express)$")
    is_enabled: bool = True
    base_eta_minutes: int = Field(..., ge=1, le=300)
    max_radius_km: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None


class DeliveryOptionUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    base_eta_minutes: Optional[int] = Field(None, ge=1, le=300)
    max_radius_km: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None


# ============================================================================
# Payment Provider Control
# ============================================================================

class PaymentProviderUpdate(BaseModel):
    provider: str = Field(..., pattern=r"^(juspay|stripe|razorpay)$")


# ============================================================================
# Notification Control
# ============================================================================

class NotificationProviderUpdate(BaseModel):
    provider: str = Field(..., pattern=r"^(twilio|meta|telegram|sms)$")


class ManualNotificationRequest(BaseModel):
    channel: str = Field(..., pattern=r"^(whatsapp|sms|telegram)$")
    recipient: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=4096)


class NotificationLogFilter(BaseModel):
    channel: Optional[str] = None
    status: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


# ============================================================================
# Dashboard
# ============================================================================

class DashboardStats(BaseModel):
    total_users: int
    total_orders: int
    total_revenue: Decimal
    orders_today: int
    revenue_today: Decimal
    active_deliveries: int
    payment_provider: str
    whatsapp_provider: str
