"""Saved delivery addresses linked to user profiles."""
from sqlalchemy import Boolean, Column, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin


class SavedAddress(Base, TimestampMixin):
    __tablename__ = "saved_addresses"

    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    label = Column(String(64), nullable=False)          # e.g. "Home", "Office"
    full_name = Column(String(128), nullable=False)
    phone = Column(String(20), nullable=False)
    line1 = Column(String(255), nullable=False)
    line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    pincode = Column(String(10), nullable=False)
    country = Column(String(64), nullable=False, default="India")
    is_default = Column(Boolean, default=False, nullable=False)
    gstin = Column(String(15), nullable=True)           # For GST invoice
