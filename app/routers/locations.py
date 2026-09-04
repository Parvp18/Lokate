from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.inventory import InventoryItem
from app.models.warehouse import Bin, Row, Warehouse
from app.schemas.location import (
    BinCreate,
    BinRead,
    RowCreate,
    RowRead,
    WarehouseCapacity,
    WarehouseCreate,
    WarehouseRead,
    WarehouseUpdate,
)

router = APIRouter(prefix="/warehouses", tags=["Warehouses"])
SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=WarehouseRead)
async def create_warehouse(data: WarehouseCreate, db: SessionDep):
    """Create a new warehouse."""
    wh = Warehouse(**data.model_dump())
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return wh


@router.get("", response_model=list[WarehouseRead])
async def list_warehouses(db: SessionDep):
    """List all warehouses."""
    res = await db.execute(select(Warehouse))
    return res.scalars().all()


@router.get("/{warehouse_id}", response_model=WarehouseRead)
async def get_warehouse(warehouse_id: int, db: SessionDep):
    """Get a specific warehouse."""
    wh = await db.get(Warehouse, warehouse_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return wh


@router.patch("/{warehouse_id}", response_model=WarehouseRead)
async def update_warehouse(warehouse_id: int, data: WarehouseUpdate, db: SessionDep):
    """Update warehouse details."""
    wh = await db.get(Warehouse, warehouse_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(wh, k, v)
        
    await db.commit()
    await db.refresh(wh)
    return wh


@router.get("/{warehouse_id}/capacity", response_model=WarehouseCapacity)
async def get_warehouse_capacity(warehouse_id: int, db: SessionDep):
    """Get the current capacity utilization for a warehouse."""
    wh = await db.get(Warehouse, warehouse_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    # Sum of all InventoryItem quantities in this warehouse
    stmt = (
        select(InventoryItem)
        .join(Bin, InventoryItem.bin_id == Bin.id)
        .join(Row, Bin.row_id == Row.id)
        .where(Row.warehouse_id == warehouse_id)
    )
    items = (await db.execute(stmt)).scalars().all()
    used = sum(i.quantity for i in items)

    return WarehouseCapacity(
        warehouse_id=wh.id,
        warehouse_code=wh.warehouse_code,
        name=wh.name,
        total_capacity=wh.storage_capacity,
        used_capacity=used,
        available_capacity=wh.storage_capacity - used,
        utilization_pct=round((used / wh.storage_capacity) * 100, 2) if wh.storage_capacity > 0 else 0,
    )


# ── Rows ─────────────────────────────────────────────────────────────────


@router.post("/{warehouse_id}/rows", response_model=RowRead)
async def create_row(warehouse_id: int, data: RowCreate, db: SessionDep):
    if data.warehouse_id != warehouse_id:
        raise HTTPException(status_code=400, detail="Warehouse ID mismatch")
    row = Row(**data.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/{warehouse_id}/rows", response_model=list[RowRead])
async def list_rows(warehouse_id: int, db: SessionDep):
    res = await db.execute(select(Row).where(Row.warehouse_id == warehouse_id))
    return res.scalars().all()


# ── Bins ─────────────────────────────────────────────────────────────────


@router.post("/{warehouse_id}/rows/{row_id}/bins", response_model=BinRead)
async def create_bin(warehouse_id: int, row_id: int, data: BinCreate, db: SessionDep):
    if data.row_id != row_id:
        raise HTTPException(status_code=400, detail="Row ID mismatch")
    
    # Verify row belongs to warehouse
    row = await db.get(Row, row_id)
    if not row or row.warehouse_id != warehouse_id:
        raise HTTPException(status_code=404, detail="Row not found in this warehouse")
        
    bin_obj = Bin(**data.model_dump())
    db.add(bin_obj)
    await db.commit()
    await db.refresh(bin_obj)
    return bin_obj


@router.get("/{warehouse_id}/rows/{row_id}/bins", response_model=list[BinRead])
async def list_bins(warehouse_id: int, row_id: int, db: SessionDep):
    res = await db.execute(select(Bin).where(Bin.row_id == row_id))
    return res.scalars().all()
