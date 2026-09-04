from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products"])
SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=ProductRead)
async def create_product(data: ProductCreate, db: SessionDep):
    product = Product(**data.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("", response_model=list[ProductRead])
async def list_products(db: SessionDep):
    res = await db.execute(select(Product))
    return res.scalars().all()


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: int, db: SessionDep):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(product_id: int, data: ProductUpdate, db: SessionDep):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(product, k, v)
        
    await db.commit()
    await db.refresh(product)
    return product
