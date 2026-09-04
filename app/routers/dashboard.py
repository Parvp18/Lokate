from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.delivery import Delivery, DeliveryStatus
from app.models.inventory import InventoryItem
from app.models.product import Product
from app.models.warehouse import Bin, Row, Warehouse
from app.schemas.dashboard import LowStockAlert, StockByRow, WarehouseSummary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/overview", response_model=list[StockByRow])
async def get_overview(db: SessionDep):
    """Stock by row, per warehouse."""
    stmt = (
        select(
            Row.warehouse_id,
            Row.label.label("row_label"),
            func.sum(InventoryItem.quantity).label("total_quantity")
        )
        .select_from(InventoryItem)
        .join(Bin, InventoryItem.bin_id == Bin.id)
        .join(Row, Bin.row_id == Row.id)
        .group_by(Row.warehouse_id, Row.label)
    )
    res = await db.execute(stmt)
    
    return [
        StockByRow(warehouse_id=r[0], row_label=r[1], total_quantity=r[2] or 0)
        for r in res.all()
    ]


@router.get("/low-stock", response_model=list[LowStockAlert])
async def get_low_stock(db: SessionDep):
    """Threshold-based low stock alert, per warehouse."""
    # We need to sum quantity per product per warehouse, then compare to threshold.
    stmt = (
        select(
            Warehouse.id.label("warehouse_id"),
            Product.id.label("product_id"),
            Product.sku,
            Product.name,
            func.sum(InventoryItem.quantity).label("current_quantity"),
            Product.reorder_threshold
        )
        .select_from(InventoryItem)
        .join(Product, InventoryItem.product_id == Product.id)
        .join(Bin, InventoryItem.bin_id == Bin.id)
        .join(Row, Bin.row_id == Row.id)
        .join(Warehouse, Row.warehouse_id == Warehouse.id)
        .group_by(Warehouse.id, Product.id)
        .having(func.sum(InventoryItem.quantity) < Product.reorder_threshold)
    )
    res = await db.execute(stmt)
    
    return [
        LowStockAlert(
            warehouse_id=r.warehouse_id,
            product_id=r.product_id,
            sku=r.sku,
            product_name=r.name,
            current_quantity=int(r.current_quantity),
            reorder_threshold=r.reorder_threshold
        )
        for r in res.all()
    ]


@router.get("/warehouse-summary", response_model=list[WarehouseSummary])
async def get_warehouse_summary(db: SessionDep):
    """Capacity utilization, active deliveries, and vendor reorder flags per warehouse."""
    # 1. Get Warehouses
    warehouses = (await db.execute(select(Warehouse))).scalars().all()
    
    # 2. Get capacity usage per warehouse
    cap_stmt = (
        select(Row.warehouse_id, func.sum(InventoryItem.quantity))
        .select_from(InventoryItem)
        .join(Bin, InventoryItem.bin_id == Bin.id)
        .join(Row, Bin.row_id == Row.id)
        .group_by(Row.warehouse_id)
    )
    cap_data = dict((await db.execute(cap_stmt)).all())
    
    # 3. Get active deliveries per warehouse
    del_stmt = (
        select(Delivery.warehouse_id, func.count(Delivery.id))
        .where(Delivery.status.in_([DeliveryStatus.PENDING, DeliveryStatus.IN_TRANSIT]))
        .group_by(Delivery.warehouse_id)
    )
    del_data = dict((await db.execute(del_stmt)).all())
    
    # 4. Get reorder flags (count of products below threshold per WH)
    low_stock_alerts = await get_low_stock(db)
    reorder_data = {}
    for alert in low_stock_alerts:
        reorder_data[alert.warehouse_id] = reorder_data.get(alert.warehouse_id, 0) + 1
        
    # Combine
    results = []
    for wh in warehouses:
        used = cap_data.get(wh.id, 0)
        utilization = round((used / wh.storage_capacity) * 100, 2) if wh.storage_capacity > 0 else 0
        
        results.append(
            WarehouseSummary(
                warehouse_id=wh.id,
                warehouse_code=wh.warehouse_code,
                name=wh.name,
                capacity_utilization_pct=utilization,
                active_deliveries_count=del_data.get(wh.id, 0),
                products_needing_reorder=reorder_data.get(wh.id, 0)
            )
        )
        
    return results
