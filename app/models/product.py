from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.vendor import vendor_product


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    category: Mapped[str] = mapped_column(String(100))
    reorder_threshold: Mapped[int] = mapped_column(Integer, default=10)

    vendors: Mapped[list["Vendor"]] = relationship(
        secondary=vendor_product, back_populates="products"
    )
    inventory_items: Mapped[list["InventoryItem"]] = relationship(back_populates="product")
