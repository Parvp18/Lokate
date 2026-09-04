from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from app.database import get_db
from app.models.delivery import Delivery, DeliveryStatus, DeliveryTrackingEvent
from app.models.order import Order, OrderStatus
from app.models.warehouse import Warehouse
from app.schemas.delivery import (
    DeliveryCreate,
    DeliveryDetail,
    DeliveryRead,
    TrackingEventCreate,
    TrackingEventRead,
)
from app.services import eta_service, routing_service

router = APIRouter(prefix="/deliveries", tags=["Deliveries"])
SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=DeliveryRead)
async def create_delivery(data: DeliveryCreate, db: SessionDep):
    """
    Create a delivery. Calls mapping APIs to calculate initial distance and ETA.
    """
    order = await db.get(Order, data.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    wh = await db.get(Warehouse, data.warehouse_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    dist, dur, eta, sev = await eta_service.predict_eta(
        wh.latitude, wh.longitude,
        data.destination_latitude, data.destination_longitude,
    )
    
    delivery = Delivery(
        order_id=data.order_id,
        warehouse_id=data.warehouse_id,
        destination_latitude=data.destination_latitude,
        destination_longitude=data.destination_longitude,
        destination_address=data.destination_address,
        distance_km=dist,
        predicted_duration_minutes=dur,
        weather_adjusted_eta=eta,
        status=DeliveryStatus.IN_TRANSIT,
        dispatched_at=datetime.now(timezone.utc),
    )
    db.add(delivery)
    await db.commit()
    await db.refresh(delivery)
    return delivery


@router.post("/{delivery_id}/tracking-events", response_model=TrackingEventRead)
async def add_tracking_event(delivery_id: int, data: TrackingEventCreate, db: SessionDep):
    """
    Add a ping to the delivery stream. Automatically updates delivery status if DELIVERED.
    """
    delivery = await db.get(Delivery, delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
        
    event = DeliveryTrackingEvent(
        delivery_id=delivery_id,
        **data.model_dump()
    )
    db.add(event)
    
    if data.status.upper() == "DELIVERED":
        delivery.status = DeliveryStatus.DELIVERED
        delivery.delivered_at = datetime.now(timezone.utc)
        
    await db.commit()
    await db.refresh(event)
    return event


@router.get("/{delivery_id}", response_model=DeliveryDetail)
async def get_delivery_status(delivery_id: int, db: SessionDep):
    """
    Get current status and recompute remaining ETA from the last known tracking ping.
    """
    stmt = (
        select(Delivery)
        .options(selectinload(Delivery.tracking_events))
        .where(Delivery.id == delivery_id)
    )
    delivery = (await db.execute(stmt)).scalar_one_or_none()
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
        
    detail = DeliveryDetail.model_validate(delivery)
    
    if delivery.tracking_events:
        latest = delivery.tracking_events[-1]
        detail.latest_event = TrackingEventRead.model_validate(latest)
        
        # If not delivered yet, recompute ETA from the last ping location
        if delivery.status in (DeliveryStatus.PENDING, DeliveryStatus.IN_TRANSIT):
            dist, dur, eta, sev = await eta_service.predict_eta(
                latest.latitude, latest.longitude,
                delivery.destination_latitude, delivery.destination_longitude,
            )
            detail.remaining_distance_km = dist
            detail.updated_eta = eta
            
    return detail


@router.get("/{delivery_id}/history", response_model=list[TrackingEventRead])
async def get_delivery_history(delivery_id: int, db: SessionDep):
    """Full tracking event stream."""
    stmt = (
        select(DeliveryTrackingEvent)
        .where(DeliveryTrackingEvent.delivery_id == delivery_id)
        .order_by(DeliveryTrackingEvent.timestamp.asc())
    )
    events = (await db.execute(stmt)).scalars().all()
    return events
