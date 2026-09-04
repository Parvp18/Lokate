# Where's Product? — Warehouse Inventory Backend

Production-ready backend for multi-warehouse inventory tracking, featuring real-time delivery ETA based on routing and live weather data.

## Features

- **Multi-Warehouse Feasibility Ranking**: Instantly ranks warehouses for fulfilling an order based on stock availability and weather-adjusted driving time.
- **Append-only Ledgers**: Immutable `StockMovement` ledger for all inventory changes, and append-only `DeliveryTrackingEvent` stream for live-tracking deliveries.
- **Live Weather Integration**: Automatically pulls from OpenWeatherMap to inflate baseline ETAs if severe weather is present along the route.
- **Live Routing**: Computes actual road distance and duration using OpenRouteService instead of naive straight-line distances.
- **Dashboards**: Full capacity utilization, low stock flags, and summary endpoints built for easy frontend consumption.

## Requirements

1. **Docker & Docker Compose**
2. **OpenWeatherMap API Key** (Free Tier): [Get key here](https://openweathermap.org/api)
3. **OpenRouteService API Key** (Free Tier): [Get key here](https://openrouteservice.org/dev/#/signup)

## Quick Start

1. Clone or download the repo.
2. Edit `.env.example` -> Rename to `.env` and insert your API keys.
3. Boot the environment and apply migrations:
   ```bash
   docker-compose up -d --build
   ```
4. Seed the database with sample data (3 warehouses, vendors, products, movements):
   ```bash
   docker-compose exec api python -m app.db.seed --reset
   ```
5. View the interactive Swagger API Docs:
   http://localhost:8000/docs

## Development & Testing

Run the test suite, which uses an isolated test database (`inventory_test`):
```bash
docker-compose exec api pytest
```

Tests include full validation of the `movement_service` transactional integrity, routing/weather aggregation mocking, and order fulfillment rankings.

## Architecture Guidelines Enforced

1. **Transactional Integrity**: `InventoryItem.quantity` is strictly driven by the `movement_service.py`. Direct writes are prohibited.
2. **Deterministic ETA adjustment**: Weather severity acts as a multiplier to the baseline travel duration (e.g. `SEVERE` = +50% travel time).
3. **Async throughout**: End-to-end `asyncio` built on FastAPI + HTTPX + SQLAlchemy 2.0 `asyncpg` bindings.
