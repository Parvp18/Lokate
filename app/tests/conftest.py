"""Shared test fixtures — async engine, session, and seeded base data."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base

# All models must be imported so Base.metadata is complete
import app.models  # noqa: F401

# Use the same DATABASE_URL but append "_test" to avoid clobbering dev data.
# In CI / docker-compose you can set DATABASE_URL to the test DB directly.
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/inventory", "/inventory_test")


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional session that rolls back after each test."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def seed_warehouse_and_bins(db: AsyncSession):
    """Seed a warehouse → row → 2 bins and return their IDs."""
    from app.models.warehouse import Warehouse, Row, Bin

    wh = Warehouse(
        warehouse_code="WH-TEST-01",
        name="Test Warehouse",
        address="123 Test St",
        latitude=19.076,
        longitude=72.877,
        storage_capacity=10000,
        point_of_contact_name="Test User",
        point_of_contact_phone="+910000000000",
        point_of_contact_email="test@test.com",
    )
    db.add(wh)
    await db.flush()

    row = Row(warehouse_id=wh.id, label="R1")
    db.add(row)
    await db.flush()

    bin_a = Bin(row_id=row.id, label="B1", location_code="WH-TEST-01-R1-B1")
    bin_b = Bin(row_id=row.id, label="B2", location_code="WH-TEST-01-R1-B2")
    db.add_all([bin_a, bin_b])
    await db.flush()

    return {"warehouse_id": wh.id, "row_id": row.id, "bin_a_id": bin_a.id, "bin_b_id": bin_b.id}


@pytest_asyncio.fixture
async def seed_product(db: AsyncSession):
    """Seed a single product and return its ID."""
    from app.models.product import Product

    product = Product(sku="TEST-SKU-001", name="Test Widget", category="Widgets", reorder_threshold=5)
    db.add(product)
    await db.flush()
    return product.id
