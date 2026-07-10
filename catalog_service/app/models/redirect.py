"""URL redirect management + usage logging."""
import enum
import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class RedirectType(int, enum.Enum):
    PERMANENT = 301
    TEMPORARY = 302


class Redirect(Base, UUIDPKMixin, TimestampMixin):
    """A source-path -> target-path redirect rule."""

    __tablename__ = "redirects"

    source_path: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    target_path: Mapped[str] = mapped_column(String(500), nullable=False)
    redirect_type: Mapped[int] = mapped_column(Integer, default=301, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    logs: Mapped[list["RedirectLog"]] = relationship(
        back_populates="redirect", cascade="all, delete-orphan"
    )


class RedirectLog(Base, UUIDPKMixin):
    """Append-only log of redirect resolutions, used for analytics/cleanup."""

    __tablename__ = "redirect_logs"

    redirect_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("redirects.id", ondelete="CASCADE"), nullable=False
    )
    resolved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    referrer: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ip_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    redirect: Mapped["Redirect"] = relationship(back_populates="logs")
