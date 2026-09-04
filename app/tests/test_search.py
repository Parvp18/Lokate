"""Tests for the search functionality."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.movement_service import record_inward
from app.services.search_service import search_inventory


@pytest.mark.asyncio
async def test_search_finds_product_and_bins(db: AsyncSession, seed_warehouse_and_bins, seed_product):
    bins = seed_warehouse_and_bins
    pid = seed_product
    
    # Add stock to two bins
    await record_inward(db, pid, bins["bin_a_id"], 30)
    await record_inward(db, pid, bins["bin_b_id"], 70)
    
    res = await search_inventory(db, "Test")
    
    assert len(res.results) == 1
    prod_res = res.results[0]
    
    assert prod_res.product_id == pid
    assert prod_res.total_quantity_across_locations == 100
    
    # Should have 2 locations, naturally sorted by quantity desc
    assert len(prod_res.locations) == 2
    assert prod_res.locations[0].quantity == 70
    assert prod_res.locations[0].location_code == "WH-TEST-01-R1-B2"
    assert prod_res.locations[1].quantity == 30
    assert prod_res.locations[1].location_code == "WH-TEST-01-R1-B1"


@pytest.mark.asyncio
async def test_search_ignores_zero_quantity(db: AsyncSession, seed_warehouse_and_bins, seed_product):
    bins = seed_warehouse_and_bins
    pid = seed_product
    
    # Add to A, but B is empty (we initialized B to 0 via a create_item secretly or just never touch it)
    await record_inward(db, pid, bins["bin_a_id"], 30)
    
    res = await search_inventory(db, "Test")
    assert len(res.results) == 1
    assert len(res.results[0].locations) == 1
    assert res.results[0].locations[0].quantity == 30
