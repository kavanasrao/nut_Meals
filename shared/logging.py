"""
Nutmeals Shared Logging Module
================================
Drop this file into any service at app/core/logging.py

Provides:
  - setup_logging()      — call once at app startup
  - get_logger(name)     — get a named logger
  - RequestLoggingMiddleware — ASGI middleware that logs every HTTP request/response
  - log_payment_event()  — structured payment log helper
  - log_notification_event() — structured notification log helper

All log records are emitted as JSON in production (ENVIRONMENT != "local")
and as human-readable text in local development.

Usage in main.py:
    from app.core.logging import setup_logging, RequestLoggingMiddleware
    setup_logging()
    app.add_middleware(RequestLoggingMiddleware)
"""
from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# ── JSON formatter ─────────────────────────────────────────────────────────────

class JsonFormatter(logging.Formatter):
    """
    Emit log records as single-line JSON objects.

    Each record contains:
      timestamp, level, logger, message, service,
      and any extra fields attached via the extra= kwarg.
    """

    def __init__(self, service_name: str = "unknown") -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "service": self.service_name,
            "message": record.getMessage(),
        }

        # Include extra fields passed via extra={} to the logging call
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "id", "levelname", "levelno", "lineno", "message",
                "module", "msecs", "msg", "name", "pathname", "process",
                "processName", "relativeCreated", "stack_info", "thread",
                "threadName",
            ):
                log_data[key] = value

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


# ── Plain text formatter ───────────────────────────────────────────────────────

class HumanFormatter(logging.Formatter):
    """Colourised, human-readable formatter for local development."""

    COLOURS = {
        "DEBUG": "\033[36m",    # cyan
        "INFO": "\033[32m",     # green
        "WARNING": "\033[33m",  # yellow
        "ERROR": "\033[31m",    # red
        "CRITICAL": "\033[35m", # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        colour = self.COLOURS.get(record.levelname, "")
        reset = self.RESET
        base = super().format(record)
        return f"{colour}{base}{reset}"


# ── Setup ──────────────────────────────────────────────────────────────────────

def setup_logging(
    service_name: str = "nutmeals",
    log_level: str = "INFO",
    environment: str = "local",
) -> None:
    """
    Configure root logger.  Call once at application startup.

    Args:
        service_name: Included in every log record.
        log_level: e.g. "DEBUG", "INFO", "WARNING".
        environment: "local" uses human-readable format; anything else uses JSON.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove any existing handlers (avoid duplicate logs in tests/reloads)
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if environment == "local":
        handler.setFormatter(
            HumanFormatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )
    else:
        handler.setFormatter(JsonFormatter(service_name=service_name))

    root_logger.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if environment == "local" else logging.WARNING
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper — returns a named logger."""
    return logging.getLogger(name)


# ── Request logging middleware ─────────────────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that logs each HTTP request and response.

    Logged fields:
      - request_id (UUID per request for correlation)
      - method, path, query_string
      - client IP
      - status_code
      - duration_ms
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        start = time.monotonic()

        logger = logging.getLogger("nutmeals.http")
        logger.info(
            "→ %s %s",
            request.method,
            request.url.path,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error(
                "✗ %s %s — EXCEPTION after %dms: %s",
                request.method,
                request.url.path,
                duration_ms,
                exc,
                exc_info=True,
                extra={"request_id": request_id, "duration_ms": duration_ms},
            )
            raise

        duration_ms = int((time.monotonic() - start) * 1000)
        log_fn = logger.warning if response.status_code >= 400 else logger.info
        log_fn(
            "← %s %s %d (%dms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


# ── Structured event helpers ───────────────────────────────────────────────────

_payment_logger = logging.getLogger("nutmeals.payment")
_notification_logger = logging.getLogger("nutmeals.notification")
_audit_logger = logging.getLogger("nutmeals.audit")


def log_payment_event(
    *,
    event: str,
    order_id: str,
    provider: str,
    amount: str,
    status: str,
    extra: dict[str, Any] | None = None,
) -> None:
    """Log a structured payment lifecycle event."""
    _payment_logger.info(
        "PAYMENT %s order=%s provider=%s amount=%s status=%s",
        event, order_id, provider, amount, status,
        extra={
            "event": event,
            "order_id": order_id,
            "provider": provider,
            "amount": amount,
            "payment_status": status,
            **(extra or {}),
        },
    )


def log_notification_event(
    *,
    event: str,
    channel: str,
    recipient: str,
    status: str,
    message_id: str = "",
    extra: dict[str, Any] | None = None,
) -> None:
    """Log a structured notification delivery event."""
    _notification_logger.info(
        "NOTIFICATION %s channel=%s recipient=%s status=%s",
        event, channel, recipient, status,
        extra={
            "event": event,
            "channel": channel,
            "recipient": recipient,
            "notification_status": status,
            "message_id": message_id,
            **(extra or {}),
        },
    )


def log_audit_event(
    *,
    admin_email: str,
    action: str,
    resource: str,
    resource_id: str = "",
    extra: dict[str, Any] | None = None,
) -> None:
    """Log an admin action for compliance / audit trail."""
    _audit_logger.info(
        "AUDIT %s by %s on %s(%s)",
        action, admin_email, resource, resource_id,
        extra={
            "action": action,
            "admin_email": admin_email,
            "resource": resource,
            "resource_id": resource_id,
            **(extra or {}),
        },
    )
