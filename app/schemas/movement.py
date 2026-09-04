from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.movement import MovementType


class MovementCreate(BaseModel):
    product_id: int
    bin_id: int
    type: MovementType
    quantity: int
    from_bin_id: int | None = None
    to_bin_id: int | None = None
    note: str | None = None


class MovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    bin_id: int
    type: MovementType
    quantity: int
    from_bin_id: int | None
    to_bin_id: int | None
    note: str | None
    created_at: datetime
