"""
Lightweight audit logging for checkout-sensitive operations (gift order
creation, subscription lifecycle changes, one-click token issuance/use).

Emits structured JSON log lines to stdout so they are picked up by the
platform's centralized log pipeline (e.g. shipped to the SIEM). This
service intentionally does not write audit logs to its own DB table to
avoid coupling audit retention policy to this service's schema migrations.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any

audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)
if not audit_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    audit_logger.addHandler(handler)


def log_audit_event(
    actor_id: str,
    action: str,
    resource: str,
    detail: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor_id": actor_id,
        "action": action,
        "resource": resource,
        "detail": detail,
        "metadata": metadata or {},
    }
    audit_logger.info(json.dumps(event))
