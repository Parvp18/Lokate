from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.delivery import DeliveryStatus


class DeliveryCreate(BaseModel):
    order_id: int
    warehouse_id: int
    destination_latitude: float
    destination_longitude: float
    destination_address: str


class DeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    warehouse_id: int
    destination_latitude: float
    destination_longitude: float
    destination_address: str
    status: DeliveryStatus
    distance_km: float | None
    predicted_duration_minutes: float | None
    weather_adjusted_eta: datetime | None
    dispatched_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime


class TrackingEventCreate(BaseModel):
    latitude: float
    longitude: float
    status: str
    note: str | None = None


class TrackingEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    delivery_id: int
    latitude: float
    longitude: float
    status: str
    timestamp: datetime
    note: str | None


class DeliveryDetail(DeliveryRead):
    latest_event: TrackingEventRead | None = None
    remaining_distance_km: float | None = None
    updated_eta: datetime | None = None
