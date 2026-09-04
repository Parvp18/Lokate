from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.search import SearchResponse
from app.services import search_service

router = APIRouter(prefix="/search", tags=["Search"])
SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=SearchResponse)
async def search(q: str, db: SessionDep):
    """
    Search for inventory by Product SKU or Name.
    Returns matching products and all bins across all warehouses that hold them,
    ranked by available quantity.
    """
    return await search_service.search_inventory(db, q)
