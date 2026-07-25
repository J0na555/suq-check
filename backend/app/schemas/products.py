from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import (
    Category,
    ConfidenceBreakdown,
    HistoryPoint,
    Pagination,
    SourceSummary,
    StoreSummary,
)


class ProductSummary(BaseModel):
    id: UUID
    canonical_name: str
    brand: str
    category: Category
    size_label: str
    market_price_etb: float = Field(gt=0)
    confidence: int = Field(ge=0, le=100)
    confidence_band: Literal["high", "medium", "low"]
    thumbnail_url: str | None = None


class ProductListResponse(Pagination):
    items: list[ProductSummary]


class ProductDetail(ProductSummary):
    barcode: str | None = None
    price_range_etb: tuple[float, float]
    evidence_count: int = Field(ge=0)
    store_count: int = Field(ge=0)
    spread_pct: float = Field(ge=0)
    updated_at: datetime
    confidence_breakdown: ConfidenceBreakdown
    sources: list[SourceSummary]
    history: list[HistoryPoint]


class NearbyStorePrice(StoreSummary):
    price_etb: float = Field(gt=0)
    confidence: int = Field(ge=0, le=100)
    updated_at: datetime
    distance_m: int | None = Field(default=None, ge=0)
    difference_from_market_etb: float
    verdict: Literal["cheap", "fair", "high"]


class NearbyStoresResponse(BaseModel):
    product_id: UUID
    market_price_etb: float = Field(gt=0)
    items: list[NearbyStorePrice]


class StoreDetail(StoreSummary):
    product_count: int = Field(ge=0)
    average_price_index: float = Field(
        description="100 is market average; below 100 is cheaper."
    )
    last_reported_at: datetime

