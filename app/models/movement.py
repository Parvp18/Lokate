from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MovementType(str, enum.Enum):
    INWARD = "INWARD"
    OUTWARD = "OUTWARD"
    TRANSFER = "TRANSFER"


class StockMovement(Base):
    """Append-only ledger of every stock change. This is the source of truth."""

    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    bin_id: Mapped[int] = mapped_column(ForeignKey("bins.id", ondelete="CASCADE"))
    type: Mapped[MovementType] = mapped_column(Enum(MovementType, name="movement_type"))
    quantity: Mapped[int] = mapped_column(Integer)
    from_bin_id: Mapped[int | None] = mapped_column(
        ForeignKey("bins.id", ondelete="SET NULL"), nullable=True
    )
    to_bin_id: Mapped[int | None] = mapped_column(
        ForeignKey("bins.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
