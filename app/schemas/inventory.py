from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class InventoryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    bin_id: int
    quantity: int
