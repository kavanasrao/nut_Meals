"""Notification control routes.

PATCH /admin/notifications/provider — switch WhatsApp/SMS/Telegram provider
GET   /admin/notifications/logs     — view notification delivery logs
POST  /admin/notifications/send     — send a manual notification
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin, require_superadmin
from app.core.db import get_db
from app.integrations.base_client import DownstreamError, ServiceUnavailableError
from app.integrations.notification_client import NotificationServiceClient
from app.models.models import AdminUser
from app.schemas.schemas import ManualNotificationRequest, NotificationProviderUpdate
from app.services.audit_service import AuditService
from app.services.config_service import ConfigService

router = APIRouter(prefix="/notifications", tags=["Notification Control"])


def _notification_client() -> NotificationServiceClient:
    return NotificationServiceClient()


@router.get("/provider", summary="Get current notification provider")
async def get_notification_provider(
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_admin),
) -> dict[str, str]:
    cfg = ConfigService(db)
    provider = await cfg.get_value("whatsapp_provider", default="twilio")
    return {"provider": provider}


@router.patch(
    "/provider",
    summary="Switch notification provider (superadmin only)",
)
async def update_notification_provider(
    request: Request,
    body: NotificationProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_superadmin),
) -> dict[str, Any]:
    # Persist in config
    cfg = ConfigService(db)
    await cfg.upsert(
        "whatsapp_provider",
        body.provider,
        description="Active WhatsApp/notification provider",
        updated_by=current_admin.email,
    )

    # Notify Notification Service (best-effort)
    try:
        await _notification_client().update_provider(body.provider)
    except (ServiceUnavailableError, DownstreamError) as exc:
        import logging
        logging.getLogger(__name__).warning(
            "Notification Service did not acknowledge provider switch: %s", exc
        )

    await AuditService(db).log(
        admin_id=str(current_admin.id),
        admin_email=current_admin.email,
        admin_role=current_admin.role.value,
        action="SWITCH_NOTIFICATION_PROVIDER",
        resource="notification_provider",
        http_method=request.method,
        http_path=str(request.url.path),
        ip_address=request.client.host if request.client else None,
        request_payload={"provider": body.provider},
        response_status=200,
    )

    return {
        "message": f"Notification provider switched to '{body.provider}'",
        "provider": body.provider,
    }


@router.get("/logs", summary="View notification delivery logs")
async def get_notification_logs(
    channel: str | None = Query(default=None),
    log_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_admin: AdminUser = Depends(require_admin),
) -> Any:
    try:
        return await _notification_client().list_logs(
            channel=channel,
            status=log_status,
            limit=limit,
            offset=offset,
        )
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except DownstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post(
    "/send",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send a manual notification to any recipient",
)
async def send_manual_notification(
    request: Request,
    body: ManualNotificationRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_admin),
) -> Any:
    try:
        result = await _notification_client().send_manual(
            channel=body.channel,
            recipient=body.recipient,
            message=body.message,
        )
    except DownstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    await AuditService(db).log(
        admin_id=str(current_admin.id),
        admin_email=current_admin.email,
        admin_role=current_admin.role.value,
        action="SEND_MANUAL_NOTIFICATION",
        resource="notification",
        http_method=request.method,
        http_path=str(request.url.path),
        ip_address=request.client.host if request.client else None,
        request_payload={"channel": body.channel, "recipient": body.recipient},
        response_status=202,
    )
    return result
