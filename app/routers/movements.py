from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.movement import MovementType, StockMovement
from app.schemas.movement import MovementCreate, MovementRead
from app.services import movement_service

router = APIRouter(prefix="/movements", tags=["Movements"])
SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=MovementRead)
async def create_movement(data: MovementCreate, db: SessionDep):
    """
    Record a stock movement safely. This will automatically update Inventory quantities.
    """
    try:
        if data.type == MovementType.INWARD:
            mov = await movement_service.record_inward(
                db, data.product_id, data.bin_id, data.quantity, data.note
            )
        elif data.type == MovementType.OUTWARD:
            mov = await movement_service.record_outward(
                db, data.product_id, data.bin_id, data.quantity, data.note
            )
        elif data.type == MovementType.TRANSFER:
            if not data.to_bin_id:
                raise HTTPException(status_code=400, detail="to_bin_id required for TRANSFER")
            mov = await movement_service.record_transfer(
                db, data.product_id, data.bin_id, data.to_bin_id, data.quantity, data.note
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid movement type")
            
        await db.commit()
        await db.refresh(mov)
        return mov
        
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except movement_service.InsufficientStockError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
        
        
@router.get("", response_model=list[MovementRead])
async def list_movements(db: SessionDep, product_id: int | None = None):
    """Ledger view. Append-only history."""
    stmt = select(StockMovement).order_by(StockMovement.created_at.desc())
    if product_id:
        stmt = stmt.where(StockMovement.product_id == product_id)
        
    res = await db.execute(stmt)
    return res.scalars().all()
