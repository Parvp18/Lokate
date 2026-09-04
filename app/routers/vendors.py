from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.product import Product
from app.models.vendor import Vendor
from app.schemas.vendor import VendorCreate, VendorRead, VendorUpdate, VendorWithProducts

router = APIRouter(prefix="/vendors", tags=["Vendors"])
SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=VendorRead)
async def create_vendor(data: VendorCreate, db: SessionDep):
    """Create a new vendor and optionally link products."""
    vendor_data = data.model_dump(exclude={"product_ids"})
    vendor = Vendor(**vendor_data)
    
    if data.product_ids:
        stmt = select(Product).where(Product.id.in_(data.product_ids))
        products = (await db.execute(stmt)).scalars().all()
        vendor.products = list(products)
        
    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)
    return vendor


@router.get("", response_model=list[VendorRead])
async def list_vendors(db: SessionDep):
    """List all vendors."""
    res = await db.execute(select(Vendor))
    return res.scalars().all()


@router.get("/{vendor_id}", response_model=VendorWithProducts)
async def get_vendor(vendor_id: int, db: SessionDep):
    """Get a specific vendor with linked products."""
    stmt = select(Vendor).options(selectinload(Vendor.products)).where(Vendor.id == vendor_id)
    vendor = (await db.execute(stmt)).scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.patch("/{vendor_id}", response_model=VendorRead)
async def update_vendor(vendor_id: int, data: VendorUpdate, db: SessionDep):
    """Update vendor details and/or linked products."""
    stmt = select(Vendor).options(selectinload(Vendor.products)).where(Vendor.id == vendor_id)
    vendor = (await db.execute(stmt)).scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
        
    update_data = data.model_dump(exclude_unset=True)
    if "product_ids" in update_data:
        p_ids = update_data.pop("product_ids")
        if p_ids:
            p_stmt = select(Product).where(Product.id.in_(p_ids))
            products = (await db.execute(p_stmt)).scalars().all()
            vendor.products = list(products)
        else:
            vendor.products = []
            
    for k, v in update_data.items():
        setattr(vendor, k, v)
        
    await db.commit()
    await db.refresh(vendor)
    return vendor


@router.get("/by-product/{sku}", response_model=list[VendorRead])
async def get_vendors_by_product_sku(sku: str, db: SessionDep):
    """Find all vendors that supply a specific product SKU."""
    stmt = select(Vendor).join(Vendor.products).where(Product.sku == sku)
    vendors = (await db.execute(stmt)).scalars().all()
    return vendors
