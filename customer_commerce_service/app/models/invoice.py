"""Invoice model for GST-compliant PDF tracking."""
import enum
import json

from sqlalchemy import Column, Enum, Integer, Numeric, String, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin


class JSONBCompat(TypeDecorator):
    """
    Stores JSON as native JSONB on PostgreSQL and as TEXT on SQLite (tests).
    Always returns a Python object on read.
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if dialect.name != "postgresql" and value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if dialect.name != "postgresql" and isinstance(value, str):
            return json.loads(value)
        return value


class InvoiceStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATED = "generated"
    FAILED = "failed"
    SENT = "sent"


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    invoice_number = Column(String(64), nullable=False, unique=True, index=True)
    order_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Billing snapshot
    billing_name = Column(String(128), nullable=False)
    billing_address = Column(String(512), nullable=False)
    billing_gstin = Column(String(15), nullable=True)

    # Amounts (in INR)
    subtotal = Column(Numeric(12, 2), nullable=False)
    cgst_rate = Column(Numeric(5, 2), nullable=False, default=9)
    sgst_rate = Column(Numeric(5, 2), nullable=False, default=9)
    igst_rate = Column(Numeric(5, 2), nullable=False, default=0)
    cgst_amount = Column(Numeric(12, 2), nullable=False)
    sgst_amount = Column(Numeric(12, 2), nullable=False)
    igst_amount = Column(Numeric(12, 2), nullable=False)
    discount_amount = Column(Numeric(12, 2), nullable=False, default=0)
    total_amount = Column(Numeric(12, 2), nullable=False)

    # Line items stored as JSONB on Postgres, TEXT on SQLite (tests)
    line_items = Column(JSONBCompat, nullable=False)

    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.PENDING, nullable=False)
    pdf_url = Column(String(512), nullable=True)       # OCI Object Storage URL
    celery_task_id = Column(String(128), nullable=True)
