"""Seed script to populate the database with hackathon-ready demo data."""

import argparse
import asyncio
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base
from app.models.delivery import Delivery, DeliveryStatus, DeliveryTrackingEvent
from app.models.movement import MovementType, StockMovement
from app.models.order import Order, OrderLineItem, OrderStatus
from app.models.product import Product
from app.models.vendor import Vendor
from app.models.warehouse import Bin, Row, Warehouse
from app.services.movement_service import record_inward, record_transfer


async def reset_db(engine):
    print("Resetting database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def seed_data(session: AsyncSession):
    print("Seeding warehouses...")
    # 3 Warehouses in different cities (India mapping for an example)
    warehouses_data = [
        {
            "warehouse_code": "WH-MUM-01",
            "name": "Mumbai Central Hub",
            "address": "Bandra Kurla Complex, Mumbai, Maharashtra 400051",
            "latitude": 19.0673,
            "longitude": 72.8659,
            "storage_capacity": 50000,
            "point_of_contact_name": "Rahul Sharma",
            "point_of_contact_phone": "+91 98765 43210",
            "point_of_contact_email": "rahul.mumbai@wheresproduct.ai",
            "operating_hours": "08:00-22:00",
        },
        {
            "warehouse_code": "WH-DEL-01",
            "name": "Delhi North Distribution",
            "address": "Okhla Industrial Estate, New Delhi, Delhi 110020",
            "latitude": 28.5492,
            "longitude": 77.2694,
            "storage_capacity": 40000,
            "point_of_contact_name": "Priya Singh",
            "point_of_contact_phone": "+91 98765 43211",
            "point_of_contact_email": "priya.delhi@wheresproduct.ai",
            "operating_hours": "00:00-23:59",  # 24/7
        },
        {
            "warehouse_code": "WH-BLR-01",
            "name": "Bangalore Tech Park Storage",
            "address": "Electronic City Phase 1, Bangalore, Karnataka 560100",
            "latitude": 12.8452,
            "longitude": 77.6602,
            "storage_capacity": 60000,
            "point_of_contact_name": "Arjun Reddy",
            "point_of_contact_phone": "+91 98765 43212",
            "point_of_contact_email": "arjun.blr@wheresproduct.ai",
            "operating_hours": "09:00-18:00",
        },
    ]

    warehouses = []
    for wd in warehouses_data:
        w = Warehouse(**wd)
        session.add(w)
        warehouses.append(w)
    await session.commit()

    all_bins = []
    for w in warehouses:
        for r in range(1, 5):  # 4 rows
            row = Row(warehouse_id=w.id, label=f"R{r}")
            session.add(row)
            await session.flush()
            
            num_bins = random.randint(10, 15)
            for b_idx in range(1, num_bins + 1):
                b = Bin(
                    row_id=row.id,
                    label=f"B{b_idx}",
                    location_code=f"{w.warehouse_code}-R{r}-B{b_idx}",
                )
                session.add(b)
                all_bins.append(b)
    await session.commit()

    print("Seeding vendors and products...")
    vendors = []
    for v_idx in range(1, 16):
        v = Vendor(
            name=f"Supplier Enterprise {v_idx}",
            contact_name=f"Contact {v_idx}",
            contact_phone=f"1800-SUPPLY-{v_idx:02d}",
            contact_email=f"sales@supplier{v_idx}.com",
            address=f"Industrial Zone {v_idx}",
        )
        session.add(v)
        vendors.append(v)
    await session.commit()

    cats = ["Electronics", "Apparel", "Home Goods", "Industrial", "Groceries"]
    products = []
    # 500 SKUs
    for p_idx in range(1, 501):
        p = Product(
            sku=f"SKU-{random.choice(['A','B','C'])}{p_idx:04d}",
            name=f"Product {p_idx} - {random.choice(['Premium', 'Standard', 'Basic'])}",
            category=random.choice(cats),
            reorder_threshold=random.randint(5, 50),
        )
        # Link 1-3 random vendors
        p.vendors = random.sample(vendors, random.randint(1, 3))
        session.add(p)
        products.append(p)
    await session.commit()

    print("Seeding stock movements (this will take a moment)...")
    # Doing 500 initial inwards so almost every product is somewhere
    for p in products:
        b = random.choice(all_bins)
        qty = random.randint(50, 500)
        # Bypassing the router to use the transactional service directly
        await record_inward(session, p.id, b.id, qty, "Initial stock")

    # Add ~100 random transfers
    for _ in range(100):
        # To do a valid transfer, we need to pick a bin that actually has stock of a product
        # but for seeding speed, we'll just inwardly add more stock to a random bin then transfer it
        p = random.choice(products)
        b_src = random.choice(all_bins)
        b_dst = random.choice(all_bins)
        if b_src.id == b_dst.id:
            continue
            
        await record_inward(session, p.id, b_src.id, 100, "Refuel for transfer")
        await record_transfer(session, p.id, b_src.id, b_dst.id, random.randint(10, 50), "Inter-bin balance")

    await session.commit()

    print("Seeding sample Deliveries and Tracking stream...")
    # Create an order
    o1 = Order(
        status=OrderStatus.FULFILLED, # Fully delivered
        destination_latitude=18.5204, # Pune
        destination_longitude=73.8567,
        destination_address="Shivajinagar, Pune, Maharashtra",
    )
    session.add(o1)
    await session.flush()
    
    oli = OrderLineItem(
        order_id=o1.id,
        product_id=products[0].id,
        quantity=5,
        fulfilled_from_warehouse_id=warehouses[0].id, # from Mumbai
    )
    session.add(oli)
    await session.flush()

    d1 = Delivery(
        order_id=o1.id,
        warehouse_id=warehouses[0].id,
        destination_latitude=o1.destination_latitude,
        destination_longitude=o1.destination_longitude,
        destination_address=o1.destination_address,
        status=DeliveryStatus.DELIVERED,
        distance_km=150.5,
        predicted_duration_minutes=180,
        weather_adjusted_eta=datetime.now(timezone.utc) - timedelta(hours=1),
        dispatched_at=datetime.now(timezone.utc) - timedelta(hours=4),
        delivered_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    session.add(d1)
    await session.flush()
    
    # Add tracking events for the completed delivery
    events = [
        ("Dispatched from Mumbai Central", 19.0673, 72.8659, 4),
        ("In transit - Navi Mumbai", 19.0330, 73.0297, 3),
        ("In transit - Lonavala", 18.7515, 73.4067, 2),
        ("Delivered", 18.5204, 73.8567, 1),
    ]
    for status, lat, lng, hours_ago in events:
        session.add(DeliveryTrackingEvent(
            delivery_id=d1.id,
            latitude=lat,
            longitude=lng,
            status=status,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        ))
        
    # Active delivery
    o2 = Order(
        status=OrderStatus.PROCESSING,
        destination_latitude=28.4595, # Gurgaon
        destination_longitude=77.0266,
        destination_address="Cyber City, Gurgaon, Haryana",
    )
    session.add(o2)
    await session.flush()
    
    d2 = Delivery(
        order_id=o2.id,
        warehouse_id=warehouses[1].id, # from Delhi
        destination_latitude=o2.destination_latitude,
        destination_longitude=o2.destination_longitude,
        destination_address=o2.destination_address,
        status=DeliveryStatus.IN_TRANSIT,
        distance_km=35.2,
        predicted_duration_minutes=45,
        weather_adjusted_eta=datetime.now(timezone.utc) + timedelta(minutes=20),
        dispatched_at=datetime.now(timezone.utc) - timedelta(minutes=25),
    )
    session.add(d2)
    await session.flush()
    
    session.add(DeliveryTrackingEvent(
        delivery_id=d2.id,
        latitude=28.5492,
        longitude=77.2694,
        status="Dispatched from Delhi North distribution",
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=25)
    ))
    session.add(DeliveryTrackingEvent(
        delivery_id=d2.id,
        latitude=28.5020,
        longitude=77.0850, # somewhere on the way
        status="In transit - heavy traffic",
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=5)
    ))

    await session.commit()
    print("Seed complete! Created 3 Warehouses, 15 Vendors, 500 Products, ~600 stock movements, and 2 deliveries.")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables first")
    args = parser.parse_args()

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    if args.reset:
        await reset_db(engine)

    # Use the session to seed
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        await seed_data(session)
        
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
