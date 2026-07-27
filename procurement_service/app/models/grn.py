import uuid
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GRNStatus, TimestampMixin, UUIDPKMixin


class GoodsReceiptNote(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "goods_receipt_notes"

    grn_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=False, index=True
    )
    status: Mapped[GRNStatus] = mapped_column(
        Enum(GRNStatus, name="grn_status"), default=GRNStatus.DRAFT, nullable=False
    )
    received_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text)

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="grns")  # noqa: F821
    items: Mapped[list["GRNItem"]] = relationship(
        back_populates="grn", cascade="all, delete-orphan"
    )


class GRNItem(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "grn_items"

    grn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("goods_receipt_notes.id"), nullable=False, index=True
    )
    purchase_order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_order_items.id"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity_received: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)

    grn: Mapped["GoodsReceiptNote"] = relationship(back_populates="items")
