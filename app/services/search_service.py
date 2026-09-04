from sqlalchemy import select, String, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import InventoryItem
from app.models.product import Product
from app.models.warehouse import Bin, Row, Warehouse
from app.schemas.search import SearchResponse, SearchResultBin, SearchResultProduct


async def search_inventory(db: AsyncSession, query: str) -> SearchResponse:
    if not query or len(query) < 2:
        return SearchResponse(query=query, results=[])

    # 1. Find matching products (ilike on SKU or Name)
    q_wild = f"%{query}%"
    stmt = (
        select(Product)
        .where(
            or_(
                Product.sku.ilike(q_wild),
                Product.name.ilike(q_wild)
            )
        )
        .limit(20)
    )
    products = (await db.execute(stmt)).scalars().all()
    
    if not products:
        return SearchResponse(query=query, results=[])

    prod_ids = [p.id for p in products]

    # 2. Get all inventory items for these products, joined with their full location hierarchy
    inv_stmt = (
        select(InventoryItem, Bin, Row, Warehouse)
        .join(Bin, InventoryItem.bin_id == Bin.id)
        .join(Row, Bin.row_id == Row.id)
        .join(Warehouse, Row.warehouse_id == Warehouse.id)
        .where(InventoryItem.product_id.in_(prod_ids))
        .where(InventoryItem.quantity > 0)
    )
    
    inv_results = (await db.execute(inv_stmt)).all()

    # 3. Group the results by product
    grouped = {p.id: [] for p in products}
    for item, bin_obj, row_obj, wh_obj in inv_results:
        # Avoid zero/negative edge cases in search results
        if item.quantity <= 0:
            continue
            
        grouped[item.product_id].append(
            SearchResultBin(
                warehouse_code=wh_obj.warehouse_code,
                warehouse_name=wh_obj.name,
                row_label=row_obj.label,
                bin_label=bin_obj.label,
                location_code=bin_obj.location_code,
                quantity=item.quantity
            )
        )

    # 4. Build response, ranked by total quantity available
    final_results = []
    for p in products:
        locs = grouped[p.id]
        if not locs:
            continue # specific product matched search but has 0 stock anywhere
            
        # sort bins by quantity desc
        locs.sort(key=lambda x: x.quantity, reverse=True)
        total = sum(l.quantity for l in locs)
        
        final_results.append(
            SearchResultProduct(
                product_id=p.id,
                sku=p.sku,
                name=p.name,
                category=p.category,
                total_quantity_across_locations=total,
                locations=locs
            )
        )

    # sort products by total stockdesc
    final_results.sort(key=lambda x: x.total_quantity_across_locations, reverse=True)
    
    return SearchResponse(query=query, results=final_results)
