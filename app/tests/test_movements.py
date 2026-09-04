"""Tests for the transactional movement service."""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import InventoryItem
from app.models.movement import MovementType, StockMovement
from app.services.movement_service import (
    InsufficientStockError,
    record_inward,
    record_outward,
    record_transfer,
)


pytestmark = pytest.mark.asyncio


# ── Inward ───────────────────────────────────────────────────────────


async def test_inward_creates_inventory_item(db: AsyncSession, seed_warehouse_and_bins, seed_product):
    bins = seed_warehouse_and_bins
    pid = seed_product

    mov = await record_inward(db, product_id=pid, bin_id=bins["bin_a_id"], quantity=50, note="initial stock")
    assert mov.type == MovementType.INWARD
    assert mov.quantity == 50

    item = (
        await db.execute(
            select(InventoryItem).where(
                InventoryItem.product_id == pid,
                InventoryItem.bin_id == bins["bin_a_id"],
            )
        )
    ).scalar_one()
    assert item.quantity == 50


async def test_inward_increments_existing(db: AsyncSession, seed_warehouse_and_bins, seed_product):
    bins = seed_warehouse_and_bins
    pid = seed_product

    await record_inward(db, pid, bins["bin_a_id"], 30)
    await record_inward(db, pid, bins["bin_a_id"], 20)

    item = (
        await db.execute(
            select(InventoryItem).where(
                InventoryItem.product_id == pid,
                InventoryItem.bin_id == bins["bin_a_id"],
            )
        )
    ).scalar_one()
    assert item.quantity == 50


async def test_inward_rejects_zero(db: AsyncSession, seed_warehouse_and_bins, seed_product):
    with pytest.raises(ValueError, match="positive"):
        await record_inward(db, seed_product, seed_warehouse_and_bins["bin_a_id"], 0)


# ── Outward ──────────────────────────────────────────────────────────


async def test_outward_decrements(db: AsyncSession, seed_warehouse_and_bins, seed_product):
    bins = seed_warehouse_and_bins
    pid = seed_product

    await record_inward(db, pid, bins["bin_a_id"], 100)
    mov = await record_outward(db, pid, bins["bin_a_id"], 40, note="order fulfillment")

    assert mov.type == MovementType.OUTWARD

    item = (
        await db.execute(
            select(InventoryItem).where(
                InventoryItem.product_id == pid,
                InventoryItem.bin_id == bins["bin_a_id"],
            )
        )
    ).scalar_one()
    assert item.quantity == 60


async def test_outward_insufficient_stock(db: AsyncSession, seed_warehouse_and_bins, seed_product):
    bins = seed_warehouse_and_bins
    pid = seed_product

    await record_inward(db, pid, bins["bin_a_id"], 10)
    with pytest.raises(InsufficientStockError) as exc_info:
        await record_outward(db, pid, bins["bin_a_id"], 20)

    assert exc_info.value.available == 10
    assert exc_info.value.requested == 20


# ── Transfer ─────────────────────────────────────────────────────────


async def test_transfer_moves_stock(db: AsyncSession, seed_warehouse_and_bins, seed_product):
    bins = seed_warehouse_and_bins
    pid = seed_product

    await record_inward(db, pid, bins["bin_a_id"], 80)
    mov = await record_transfer(db, pid, bins["bin_a_id"], bins["bin_b_id"], 30)

    assert mov.type == MovementType.TRANSFER
    assert mov.from_bin_id == bins["bin_a_id"]
    assert mov.to_bin_id == bins["bin_b_id"]

    src = (
        await db.execute(
            select(InventoryItem).where(
                InventoryItem.product_id == pid,
                InventoryItem.bin_id == bins["bin_a_id"],
            )
        )
    ).scalar_one()
    assert src.quantity == 50

    dst = (
        await db.execute(
            select(InventoryItem).where(
                InventoryItem.product_id == pid,
                InventoryItem.bin_id == bins["bin_b_id"],
            )
        )
    ).scalar_one()
    assert dst.quantity == 30


async def test_transfer_insufficient_stock(db: AsyncSession, seed_warehouse_and_bins, seed_product):
    bins = seed_warehouse_and_bins
    pid = seed_product

    await record_inward(db, pid, bins["bin_a_id"], 5)
    with pytest.raises(InsufficientStockError):
        await record_transfer(db, pid, bins["bin_a_id"], bins["bin_b_id"], 10)


async def test_transfer_same_bin_rejected(db: AsyncSession, seed_warehouse_and_bins, seed_product):
    bins = seed_warehouse_and_bins
    pid = seed_product

    await record_inward(db, pid, bins["bin_a_id"], 10)
    with pytest.raises(ValueError, match="same bin"):
        await record_transfer(db, pid, bins["bin_a_id"], bins["bin_a_id"], 5)


# ── Ledger integrity ────────────────────────────────────────────────


async def test_every_change_has_a_movement_row(db: AsyncSession, seed_warehouse_and_bins, seed_product):
    """Verify that each operation creates exactly one StockMovement row."""
    bins = seed_warehouse_and_bins
    pid = seed_product

    await record_inward(db, pid, bins["bin_a_id"], 100)
    await record_outward(db, pid, bins["bin_a_id"], 10)
    await record_transfer(db, pid, bins["bin_a_id"], bins["bin_b_id"], 20)

    movements = (
        await db.execute(select(StockMovement).where(StockMovement.product_id == pid))
    ).scalars().all()

    assert len(movements) == 3
    types = [m.type for m in movements]
    assert types == [MovementType.INWARD, MovementType.OUTWARD, MovementType.TRANSFER]
