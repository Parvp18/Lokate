# Demo Script / Pitch Guide

If you are demoing this for a hackathon, run these API calls sequentially via Postman or `curl` to step through the system's core capabilities.

> **Ensure you have run the seed script first!**
> `docker-compose exec api python -m app.db.seed --reset`

## 1. Show the Executive Dashboard (Capacity & Needs)

*Goal: Show that we can instantly see which warehouse needs restocks and is at capacity.*

```bash
curl -s http://localhost:8000/dashboard/warehouse-summary | jq .
```
- Highlights `capacity_utilization_pct`
- Highlights `products_needing_reorder`

## 2. Who supplies the low stock? 

*Goal: Find out how to reach the vendor for a deeply depleted product.*

Grab a `sku` from the `products_needing_reorder` count using the low-stock endpoint:
```bash
curl -s http://localhost:8000/dashboard/low-stock | jq .
```

Take a SKU from that list, and lookup the vendor contact card:
```bash
curl -s http://localhost:8000/vendors/by-product/SKU-A0012 | jq .
```
- Instantly returns the `contact_name`, `contact_phone`, and `contact_email` to reorder.

## 3. Order Intake & Multi-Warehouse Feasibility Ranking

*Goal: An order is placed for delivery to Bangalore. Which warehouse should fulfill it?*

Pick a product that is available in multiple warehouses, and submit an order:

```bash
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "destination_latitude": 12.9352,
    "destination_longitude": 77.6245,
    "destination_address": "Koramangala, Bangalore",
    "line_items": [
      {
        "product_id": 1,
        "quantity": 10
      }
    ]
  }' | jq .
```
- **Focus on the `fulfillment` array in the response.** 
- The system will query stock to find candidate warehouses.
- It concurrently pings OpenRouteService and OpenWeatherMap for each candidate.
- It ranks the candidate in the `top_pick` field and lists others in `alternatives`. 
- Observe the `reason` field: e.g. `ETA 150m (MODERATE weather), 120km`

## 4. Live Delivery Tracking & ETA adjustments

*Goal: We dispatched the order. Show the live tracking stream and remaining ETA updating.*

The seed script creates two sample deliveries (one delivered, one in transit). Get the active one:

1. List deliveries to find the IN_TRANSIT one:
```bash
curl -s http://localhost:8000/deliveries | jq '.[] | select(.status=="IN_TRANSIT")'
```

2. Note its ID (e.g. `2`). Fetch its current status, which calculates real-time ETA from its LAST KNOWN ping:
```bash
curl -s http://localhost:8000/deliveries/2 | jq .
```
- See the `latest_event` and `remaining_distance_km`.

3. Push a live GPS ping from the truck driver app (simulate moving closer to the destination):
```bash
curl -X POST http://localhost:8000/deliveries/2/tracking-events \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 28.4595,
    "longitude": 77.0266,
    "status": "Entering city limits"
  }'
```

4. Now fetch the delivery detail again as the customer:
```bash
curl -s http://localhost:8000/deliveries/2 | jq .
```
- Notice that the `remaining_distance_km` has shrunk and `updated_eta` has adjusted instantly based on the new coordinates!
