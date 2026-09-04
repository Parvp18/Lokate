from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import InventoryItem
from app.models.movement import MovementType, StockMovement


class InsufficientStockError(Exception):
    """Raised when an outward/transfer exceeds available quantity."""

    def __init__(self, product_id: int, bin_id: int, available: int, requested: int):
        self.product_id = product_id
        self.bin_id = bin_id
        self.available = available
        self.requested = requested
        super().__init__(
            f"Insufficient stock for product {product_id} in bin {bin_id}: "
            f"available={available}, requested={requested}"
        )


async def _get_or_create_item(
    session: AsyncSession, product_id: int, bin_id: int
) -> InventoryItem:
    """Fetch the InventoryItem row, creating one (qty=0) if it doesn't exist."""
    stmt = select(InventoryItem).where(
        InventoryItem.product_id == product_id,
        InventoryItem.bin_id == bin_id,
    )
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        item = InventoryItem(product_id=product_id, bin_id=bin_id, quantity=0)
        session.add(item)
        await session.flush()
    return item


async def record_inward(
    session: AsyncSession,
    product_id: int,
    bin_id: int,
    quantity: int,
    note: str | None = None,
) -> StockMovement:
    """Add stock to a bin. Creates the InventoryItem if needed."""
    if quantity <= 0:
        raise ValueError("Inward quantity must be positive")

    item = await _get_or_create_item(session, product_id, bin_id)
    item.quantity += quantity

    movement = StockMovement(
        product_id=product_id,
        bin_id=bin_id,
        type=MovementType.INWARD,
        quantity=quantity,
        note=note,
    )
    session.add(movement)
    await session.flush()
    return movement


async def record_outward(
    session: AsyncSession,
    product_id: int,
    bin_id: int,
    quantity: int,
    note: str | None = None,
) -> StockMovement:
    """Remove stock from a bin. Raises InsufficientStockError if not enough."""
    if quantity <= 0:
        raise ValueError("Outward quantity must be positive")

    item = await _get_or_create_item(session, product_id, bin_id)
    if item.quantity < quantity:
        raise InsufficientStockError(product_id, bin_id, item.quantity, quantity)

    item.quantity -= quantity

    movement = StockMovement(
        product_id=product_id,
        bin_id=bin_id,
        type=MovementType.OUTWARD,
        quantity=quantity,
        note=note,
    )
    session.add(movement)
    await session.flush()
    return movement


async def record_transfer(
    session: AsyncSession,
    product_id: int,
    from_bin_id: int,
    to_bin_id: int,
    quantity: int,
    note: str | None = None,
) -> StockMovement:
    """Move stock between bins atomically. Raises InsufficientStockError if source is short."""
    if quantity <= 0:
        raise ValueError("Transfer quantity must be positive")
    if from_bin_id == to_bin_id:
        raise ValueError("Cannot transfer to the same bin")

    # Decrease source
    source = await _get_or_create_item(session, product_id, from_bin_id)
    if source.quantity < quantity:
        raise InsufficientStockError(product_id, from_bin_id, source.quantity, quantity)
    source.quantity -= quantity

    # Increase destination
    dest = await _get_or_create_item(session, product_id, to_bin_id)
    dest.quantity += quantity

    movement = StockMovement(
        product_id=product_id,
        bin_id=from_bin_id,
        type=MovementType.TRANSFER,
        quantity=quantity,
        from_bin_id=from_bin_id,
        to_bin_id=to_bin_id,
        note=note,
    )
    session.add(movement)
    await session.flush()
    return movement
