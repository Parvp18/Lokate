from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine
from app.routers import inventory, locations, movements, products, vendors, search, orders, deliveries, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: nothing extra needed — Alembic handles migrations
    yield
    # Shutdown: dispose the engine connection pool
    await engine.dispose()


app = FastAPI(
    title="Where's Product — Warehouse Inventory API",
    description="Multi-warehouse inventory location tracking with live delivery ETA",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(locations.router)
app.include_router(vendors.router)
app.include_router(products.router)
app.include_router(inventory.router)
app.include_router(movements.router)
app.include_router(search.router)
app.include_router(orders.router)
app.include_router(deliveries.router)
app.include_router(dashboard.router)


@app.get("/health", summary="Health check")
async def health():
    return {"status": "ok"}
