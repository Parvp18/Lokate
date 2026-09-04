"""Tests for order feasibility ranking across multiple warehouses."""

from unittest.mock import patch
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.order import OrderLineItemCreate
from app.services.movement_service import record_inward
from app.services.pick_suggestion import rank_warehouses_for_order


@pytest.mark.asyncio
@patch("app.services.eta_service.predict_eta")
async def test_rank_warehouses(mock_predict, db: AsyncSession, seed_warehouse_and_bins, seed_product):
    """
    We seed 1 warehouse with 2 bins. 
    We'll test the basic ranking structure. A full multi-warehouse test would require
    seeding more warehouses, but this verifies the DB hit, aggregation, and sorting.
    """
    bins = seed_warehouse_and_bins
    pid = seed_product
    
    await record_inward(db, pid, bins["bin_a_id"], 20)
    await record_inward(db, pid, bins["bin_b_id"], 10)
    
    # 20+10 = 30 total in this warehouse
    mock_predict.return_value = (50.0, 60.0, None, "CLEAR")  # mock raw ETA response: dist, dur, eta, sev
    
    # To mock the datetimes easily without freezing time, we patch datetime inside pick_suggestion
    import datetime
    from datetime import timezone
    future_time = datetime.datetime.now(timezone.utc) + datetime.timedelta(minutes=60)
    mock_predict.return_value = (50.0, 60.0, future_time, "CLEAR")

    li = OrderLineItemCreate(product_id=pid, quantity=25)
    
    res = await rank_warehouses_for_order(db, li, 0.0, 0.0)
    
    assert res.product_id == pid
    assert res.requested_quantity == 25
    assert res.top_pick is not None
    assert res.top_pick.warehouse_id == bins["warehouse_id"]
    assert res.top_pick.available_quantity == 30
    assert res.top_pick.can_fully_fulfill is True


@pytest.mark.asyncio
@patch("app.services.eta_service.predict_eta")
async def test_rank_warehouses_insufficient_stock_is_penalized(mock_predict, db: AsyncSession, seed_warehouse_and_bins, seed_product):
    bins = seed_warehouse_and_bins
    pid = seed_product
    
    await record_inward(db, pid, bins["bin_a_id"], 5)
    
    import datetime
    from datetime import timezone
    future_time = datetime.datetime.now(timezone.utc) + datetime.timedelta(minutes=60)
    mock_predict.return_value = (50.0, 60.0, future_time, "CLEAR")

    li = OrderLineItemCreate(product_id=pid, quantity=25)
    
    res = await rank_warehouses_for_order(db, li, 0.0, 0.0)
    
    assert res.top_pick is not None
    assert res.top_pick.available_quantity == 5
    assert res.top_pick.can_fully_fulfill is False
    # Score should be > 1,000,000 due to penalty
    assert res.top_pick.score > 1000000
