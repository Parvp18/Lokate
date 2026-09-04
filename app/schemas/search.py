from pydantic import BaseModel, ConfigDict


class SearchResultBin(BaseModel):
    warehouse_code: str
    warehouse_name: str
    row_label: str
    bin_label: str
    location_code: str
    quantity: int


class SearchResultProduct(BaseModel):
    product_id: int
    sku: str
    name: str
    category: str
    total_quantity_across_locations: int
    locations: list[SearchResultBin]


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultProduct]
