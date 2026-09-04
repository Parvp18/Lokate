from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Many-to-many join table: Vendor <-> Product
vendor_product = Table(
    "vendor_product",
    Base.metadata,
    Column("vendor_id", Integer, ForeignKey("vendors.id", ondelete="CASCADE"), primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
)


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    contact_name: Mapped[str] = mapped_column(String(200))
    contact_phone: Mapped[str] = mapped_column(String(30))
    contact_email: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(String(500))

    products: Mapped[list["Product"]] = relationship(
        secondary=vendor_product, back_populates="vendors"
    )
