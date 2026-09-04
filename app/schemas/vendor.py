from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class VendorCreate(BaseModel):
    name: str
    contact_name: str
    contact_phone: str
    contact_email: str
    address: str
    product_ids: list[int] = []


class VendorUpdate(BaseModel):
    name: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    address: str | None = None
    product_ids: list[int] | None = None


class VendorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    contact_name: str
    contact_phone: str
    contact_email: str
    address: str


class VendorWithProducts(VendorRead):
    products: list[ProductBrief] = []


class ProductBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str


# Rebuild to resolve forward reference
VendorWithProducts.model_rebuild()
