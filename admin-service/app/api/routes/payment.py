"""Payment provider control routes.

PATCH /admin/payment/provider  — switch provider dynamically
GET   /admin/payment/provider  — get current provider

The provider switch:
  1. Updates the system_config table (payment_provider key).
  2. Notifies the Payment Service via its REST API so it can reload.
  3. Writes an audit log entry.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_superadmin
from app.core.db import get_db
from app.integrations.base_client import DownstreamError, ServiceUnavailableError
from app.integrations.payment_client import PaymentServiceClient
from app.models.models import AdminUser
from app.schemas.schemas import PaymentProviderUpdate
from app.services.audit_service import AuditService
from app.services.config_service import ConfigService

router = APIRouter(prefix="/payment", tags=["Payment Control"])


@router.get("/provider", summary="Get current payment provider")
async def get_payment_provider(
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_superadmin),
) -> dict[str, str]:
    cfg = ConfigService(db)
    provider = await cfg.get_value("payment_provider", default="juspay")
    return {"provider": provider}


@router.patch(
    "/provider",
    summary="Switch payment provider (superadmin only)",
)
async def update_payment_provider(
    request: Request,
    body: PaymentProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_superadmin),
) -> dict[str, Any]:
    # 1. Persist in config table
    cfg = ConfigService(db)
    await cfg.upsert(
        "payment_provider",
        body.provider,
        description="Active payment gateway provider",
        updated_by=current_admin.email,
    )

    # 2. Notify Payment Service (best-effort — service may restart and read from config)
    try:
        await PaymentServiceClient().update_provider(body.provider)
    except (ServiceUnavailableError, DownstreamError) as exc:
        # Log warning but don't fail — the service will pick up the new provider
        # on restart via its own config polling / DB read
        import logging
        logging.getLogger(__name__).warning(
            "Payment Service did not acknowledge provider switch: %s", exc
        )

    # 3. Audit log
    await AuditService(db).log(
        admin_id=str(current_admin.id),
        admin_email=current_admin.email,
        admin_role=current_admin.role.value,
        action="SWITCH_PAYMENT_PROVIDER",
        resource="payment_provider",
        http_method=request.method,
        http_path=str(request.url.path),
        ip_address=request.client.host if request.client else None,
        request_payload={"provider": body.provider},
        response_status=200,
    )

    return {"message": f"Payment provider switched to '{body.provider}'", "provider": body.provider}
