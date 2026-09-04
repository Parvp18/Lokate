import math
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import InventoryItem
from app.models.product import Product
from app.models.warehouse import Bin, Row, Warehouse
from app.schemas.order import OrderLineItemCreate, WarehouseCandidate, LineItemFulfillment
from app.services import eta_service


async def rank_warehouses_for_order(
    db: AsyncSession,
    line_item: OrderLineItemCreate,
    dest_lat: float,
    dest_lng: float
) -> LineItemFulfillment:
    """
    Finds and ranks candidate warehouses that can fulfill a line item.
    Ranking criteria:
    1. Can it fully fulfill the quantity? (Yes gets priority)
    2. ETA (Weather adjusted duration)
    3. Baseline duration
    """
    # 1. Fetch product
    prod = await db.get(Product, line_item.product_id)
    if not prod:
        return LineItemFulfillment(
            product_id=line_item.product_id,
            sku="UNKNOWN",
            requested_quantity=line_item.quantity
        )
        
    # 2. Find total quantity available for this product GROUPED BY WAREHOUSE
    # We query InventoryItem -> Bin -> Row -> Warehouse
    stmt = (
        select(Warehouse, InventoryItem)
        .join(Row, Warehouse.id == Row.warehouse_id)
        .join(Bin, Row.id == Bin.row_id)
        .join(InventoryItem, Bin.id == InventoryItem.bin_id)
        .where(InventoryItem.product_id == line_item.product_id)
        .where(InventoryItem.quantity > 0)
    )
    result = (await db.execute(stmt)).all()
    
    wh_capacity = {}  # warehouse_id -> [WarehouseObj, total_qty_for_product]
    for wh, item in result:
        if wh.id not in wh_capacity:
            wh_capacity[wh.id] = [wh, 0]
        wh_capacity[wh.id][1] += item.quantity
        
    if not wh_capacity:
        # None available anywhere
        return LineItemFulfillment(
            product_id=prod.id,
            sku=prod.sku,
            requested_quantity=line_item.quantity
        )

    # 3. For each candidate warehouse, get ETA prediction concurrently
    candidates = []
    
    import asyncio
    
    async def process_candidate(wh: Warehouse, total_qty: int):
        can_fulfill = total_qty >= line_item.quantity
        
        c = WarehouseCandidate(
            warehouse_id=wh.id,
            warehouse_code=wh.warehouse_code,
            warehouse_name=wh.name,
            available_quantity=total_qty,
            can_fully_fulfill=can_fulfill
        )
        
        try:
            dist, dur, eta_time, sev = await eta_service.predict_eta(
                wh.latitude, wh.longitude, dest_lat, dest_lng
            )
            c.distance_km = dist
            c.duration_minutes = dur
            
            # For ranking, use the ETA minutes adjusted by weather
            now = datetime.now(timezone.utc)
            from datetime import datetime, timezone
            # Convert timedelta to minutes directly from the ETA vs Now difference for scoring
            c.weather_adjusted_eta_minutes = float((eta_time - datetime.now(timezone.utc)).total_seconds() / 60)
            
            # Simple scoring: Lower score is better.
            # If it can't fulfill fully, add a massive penalty (1,000,000)
            penalty = 0 if can_fulfill else 1000000
            
            # Score = penalty + weather_adjusted_ETA (so faster delivery wins)
            c.score = penalty + c.weather_adjusted_eta_minutes
            
            c.reason = f"ETA {math.ceil(c.weather_adjusted_eta_minutes)}m ({sev} weather), {dist}km"
            
        except Exception as e:
            # Fallback if API fails: penalize stringly but don't drop
            c.score = 500000 if can_fulfill else 2000000
            c.reason = "ETA lookup failed"

        return c
        
    tasks = [process_candidate(wh, qty) for wh, qty in wh_capacity.values()]
    candidates = await asyncio.gather(*tasks)
    
    # 4. Sort candidates
    candidates.sort(key=lambda c: c.score or 0)
    
    top = candidates[0] if candidates else None
    alts = candidates[1:] if len(candidates) > 1 else []
    
    return LineItemFulfillment(
        product_id=prod.id,
        sku=prod.sku,
        requested_quantity=line_item.quantity,
        top_pick=top,
        alternatives=alts
    )
