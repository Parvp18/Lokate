from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.inventory import InventoryItem
from app.schemas.inventory import InventoryItemRead

router = APIRouter(prefix="/inventory", tags=["Inventory"])
SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[InventoryItemRead])
async def list_inventory(
    db: SessionDep,
    product_id: int | None = None,
    bin_id: int | None = None,
):
    """
    List inventory items. Can be filtered by product or bin.
    Quantity updates MUST go through the /movements endpoints.
    """
    stmt = select(InventoryItem)
    if product_id:
        stmt = stmt.where(InventoryItem.product_id == product_id)
    if bin_id:
        stmt = stmt.where(InventoryItem.bin_id == bin_id)
        
    res = await db.execute(stmt)
    return res.scalars().all()
