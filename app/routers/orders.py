from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.order import Order, OrderLineItem
from app.schemas.order import OrderCreate, OrderFulfillmentResponse, OrderRead
from app.services import pick_suggestion

router = APIRouter(prefix="/orders", tags=["Orders"])
SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=OrderFulfillmentResponse)
async def create_order_with_fulfillment_plan(data: OrderCreate, db: SessionDep):
    """
    Intake a new order. For each line item, this will:
    1. Query stock across all warehouses.
    2. Compute real driving distance & weather-adjusted ETA to the destination.
    3. Rank the best warehouse to fulfill each item from.
    """
    # 1. Create the Order
    order = Order(
        destination_latitude=data.destination_latitude,
        destination_longitude=data.destination_longitude,
        destination_address=data.destination_address,
    )
    db.add(order)
    await db.flush() # get order id
    
    # 2. For each line item, analyze fulfillment options
    fulfillments = []
    
    for li_schema in data.line_items:
        # Rank warehouses
        fulfillment = await pick_suggestion.rank_warehouses_for_order(
            db, 
            li_schema, 
            data.destination_latitude, 
            data.destination_longitude
        )
        fulfillments.append(fulfillment)
        
        # Decide based on top pick
        picked_wh_id = None
        if fulfillment.top_pick and fulfillment.top_pick.can_fully_fulfill:
            picked_wh_id = fulfillment.top_pick.warehouse_id
            
        line_item = OrderLineItem(
            order_id=order.id,
            product_id=li_schema.product_id,
            quantity=li_schema.quantity,
            fulfilled_from_warehouse_id=picked_wh_id,
            # We skip picking the exact BIN here for brevity, the prompt says resolve candidate *warehouses*
        )
        db.add(line_item)
        
    await db.commit()
    
    # Reload with relationships
    stmt = select(Order).options(selectinload(Order.line_items)).where(Order.id == order.id)
    order_loaded = (await db.execute(stmt)).scalar_one()

    return OrderFulfillmentResponse(
        order=OrderRead.model_validate(order_loaded),
        fulfillment=fulfillments
    )


@router.get("", response_model=list[OrderRead])
async def list_orders(db: SessionDep):
    stmt = select(Order).options(selectinload(Order.line_items))
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: int, db: SessionDep):
    stmt = select(Order).options(selectinload(Order.line_items)).where(Order.id == order_id)
    order = (await db.execute(stmt)).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
