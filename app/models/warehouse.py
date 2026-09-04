from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    warehouse_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(String(500))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    storage_capacity: Mapped[int] = mapped_column(Integer, comment="Total unit capacity")
    point_of_contact_name: Mapped[str] = mapped_column(String(200))
    point_of_contact_phone: Mapped[str] = mapped_column(String(30))
    point_of_contact_email: Mapped[str] = mapped_column(String(200))
    operating_hours: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    rows: Mapped[list[Row]] = relationship(back_populates="warehouse", cascade="all, delete-orphan")


class Row(Base):
    __tablename__ = "rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(50))

    warehouse: Mapped[Warehouse] = relationship(back_populates="rows")
    bins: Mapped[list[Bin]] = relationship(back_populates="row", cascade="all, delete-orphan")


class Bin(Base):
    __tablename__ = "bins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    row_id: Mapped[int] = mapped_column(ForeignKey("rows.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(50))
    location_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    row: Mapped[Row] = relationship(back_populates="bins")
    inventory_items: Mapped[list["InventoryItem"]] = relationship(back_populates="bin")
