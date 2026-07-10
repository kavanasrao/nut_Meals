"""
WAF (Web Application Firewall) models.

Rules are stored in the DB (not hardcoded) so security admins can tune
detection without a redeploy. The middleware layer (app/middleware/waf_middleware.py)
loads active rules (cached in Redis) and evaluates each request against them.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WafRuleType(str, enum.Enum):
    SQLI = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    RATE_LIMIT = "rate_limit"
    CUSTOM_REGEX = "custom_regex"
    IP_BLOCKLIST = "ip_blocklist"


class WafAction(str, enum.Enum):
    BLOCK = "block"
    LOG_ONLY = "log_only"
    CHALLENGE = "challenge"  # e.g. reserved for future CAPTCHA integration


class WafRule(Base):
    """A single configurable WAF detection rule.

    `pattern` semantics depend on `rule_type`:
      - SQLI / XSS / CUSTOM_REGEX: a Python regex evaluated against
        path, query string, headers, and (size-limited) body.
      - IP_BLOCKLIST: a CIDR or exact IP string.
      - RATE_LIMIT: pattern holds JSON like {"window_s": 60, "max_requests": 100}.
    """

    __tablename__ = "waf_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    rule_type: Mapped[WafRuleType] = mapped_column(Enum(WafRuleType), nullable=False, index=True)
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[WafAction] = mapped_column(Enum(WafAction), default=WafAction.BLOCK, nullable=False)
    severity: Mapped[int] = mapped_column(Integer, default=5)  # 1 (low) - 10 (critical)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    applies_to_service: Mapped[str | None] = mapped_column(
        String(64), nullable=True, doc="If null, rule applies to all services"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class WafIncident(Base):
    """A record of a request that matched one or more WAF rules.

    Kept separate from generic AuditLog because WAF incidents have their own
    high-volume write pattern and retention/alerting requirements (e.g. feed
    into a SIEM), even though both ultimately support compliance reporting.
    """

    __tablename__ = "waf_incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_type: Mapped[WafRuleType] = mapped_column(Enum(WafRuleType), nullable=False)
    action_taken: Mapped[WafAction] = mapped_column(Enum(WafAction), nullable=False)
    source_ip: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    service: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    matched_fragment: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Truncated snippet of the offending input, for triage"
    )
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
