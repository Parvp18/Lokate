from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.order import OrderStatus


class OrderLineItemCreate(BaseModel):
    product_id: int
    quantity: int


class OrderCreate(BaseModel):
    destination_latitude: float
    destination_longitude: float
    destination_address: str
    line_items: list[OrderLineItemCreate]


class OrderLineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    product_id: int
    quantity: int
    fulfilled_from_warehouse_id: int | None
    fulfilled_from_bin_id: int | None


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OrderStatus
    destination_latitude: float
    destination_longitude: float
    destination_address: str
    created_at: datetime
    updated_at: datetime
    line_items: list[OrderLineItemRead] = []


class WarehouseCandidate(BaseModel):
    warehouse_id: int
    warehouse_code: str
    warehouse_name: str
    available_quantity: int
    can_fully_fulfill: bool
    distance_km: float | None = None
    duration_minutes: float | None = None
    weather_adjusted_eta_minutes: float | None = None
    score: float | None = None
    reason: str | None = None


class OrderFulfillmentResponse(BaseModel):
    order: OrderRead
    fulfillment: list[LineItemFulfillment] = []


class LineItemFulfillment(BaseModel):
    product_id: int
    sku: str
    requested_quantity: int
    top_pick: WarehouseCandidate | None = None
    alternatives: list[WarehouseCandidate] = []


# Rebuild forward ref
OrderFulfillmentResponse.model_rebuild()
