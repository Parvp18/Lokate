from pydantic import BaseModel


class StockByRow(BaseModel):
    warehouse_id: int
    row_label: str
    total_quantity: int


class LowStockAlert(BaseModel):
    warehouse_id: int
    product_id: int
    sku: str
    product_name: str
    current_quantity: int
    reorder_threshold: int


class WarehouseSummary(BaseModel):
    warehouse_id: int
    warehouse_code: str
    name: str
    capacity_utilization_pct: float
    active_deliveries_count: int
    products_needing_reorder: int
