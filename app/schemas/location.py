from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ── Warehouse ────────────────────────────────────────────────────────


class WarehouseCreate(BaseModel):
    warehouse_code: str
    name: str
    address: str
    latitude: float
    longitude: float
    storage_capacity: int
    point_of_contact_name: str
    point_of_contact_phone: str
    point_of_contact_email: str
    operating_hours: str | None = None


class WarehouseUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    storage_capacity: int | None = None
    point_of_contact_name: str | None = None
    point_of_contact_phone: str | None = None
    point_of_contact_email: str | None = None
    operating_hours: str | None = None


class WarehouseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warehouse_code: str
    name: str
    address: str
    latitude: float
    longitude: float
    storage_capacity: int
    point_of_contact_name: str
    point_of_contact_phone: str
    point_of_contact_email: str
    operating_hours: str | None
    created_at: datetime
    updated_at: datetime


class WarehouseCapacity(BaseModel):
    warehouse_id: int
    warehouse_code: str
    name: str
    total_capacity: int
    used_capacity: int
    available_capacity: int
    utilization_pct: float


# ── Row / Bin ────────────────────────────────────────────────────────


class RowCreate(BaseModel):
    warehouse_id: int
    label: str


class RowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warehouse_id: int
    label: str


class BinCreate(BaseModel):
    row_id: int
    label: str
    location_code: str


class BinRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    row_id: int
    label: str
    location_code: str
