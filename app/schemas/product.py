from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ProductCreate(BaseModel):
    sku: str
    name: str
    category: str
    reorder_threshold: int = 10


class ProductUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    reorder_threshold: int | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    category: str
    reorder_threshold: int
