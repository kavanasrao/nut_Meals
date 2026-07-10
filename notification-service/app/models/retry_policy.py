import uuid

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class RetryPolicy(Base):
    """Per-channel configurable retry policy, editable without a redeploy."""
    __tablename__ = "retry_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=5)
    base_backoff_seconds: Mapped[int] = mapped_column(Integer, default=30)
    max_backoff_seconds: Mapped[int] = mapped_column(Integer, default=3600)
    jitter: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
