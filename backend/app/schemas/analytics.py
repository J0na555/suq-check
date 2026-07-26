from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import Category

ComplianceBand = Literal["at", "above", "below"]


class TrendPoint(BaseModel):
    day: date
    price_etb: float


class ProductTrend(BaseModel):
    product_id: UUID
    product_name: str
    direction: Literal["up", "down", "stable"]
    change_pct: float
    points: list[TrendPoint]


class TrendsResponse(BaseModel):
    period_days: int
    items: list[ProductTrend]


class ComplianceSummary(BaseModel):
    shops_priced: int = Field(ge=0)
    at_mrp: int = Field(ge=0)
    above_mrp: int = Field(ge=0)
    below_mrp: int = Field(ge=0)
    at_pct: float = Field(ge=0, le=100)
    above_pct: float = Field(ge=0, le=100)
    below_pct: float = Field(ge=0, le=100)


class ComplianceRow(BaseModel):
    product_id: UUID
    product_name: str
    brand: str
    category: Category
    mrp_etb: float = Field(gt=0)
    market_price_etb: float = Field(gt=0)
    delta_pct: float
    band: ComplianceBand
    store_count: int = Field(ge=0)
    at_mrp: int = Field(ge=0)
    above_mrp: int = Field(ge=0)
    below_mrp: int = Field(ge=0)


class ComplianceResponse(BaseModel):
    summary: ComplianceSummary
    items: list[ComplianceRow]


class DistrictRow(BaseModel):
    district: str
    avg_price_etb: float = Field(gt=0)
    avg_mrp_etb: float | None = Field(default=None, gt=0)
    vs_mrp_pct: float | None = None
    priced_cells: int = Field(ge=0)
    oos_cells: int = Field(ge=0)
    oos_rate_pct: float = Field(ge=0, le=100)
    at_mrp_pct: float | None = Field(default=None, ge=0, le=100)


class DistrictsResponse(BaseModel):
    items: list[DistrictRow]


class OosAlert(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    brand: str
    category: Category
    store_id: UUID | None = None
    store_name: str | None = None
    district: str | None = None
    observed_at: datetime
    source_type: str


class OosResponse(BaseModel):
    period_days: int
    total: int = Field(ge=0)
    items: list[OosAlert]


class CompetitorRow(BaseModel):
    product_id: UUID
    product_name: str
    brand: str
    category: Category
    market_price_etb: float = Field(gt=0)
    mrp_etb: float | None = Field(default=None, gt=0)
    vs_category_median_pct: float
    change_pct: float
    direction: Literal["up", "down", "stable"]
    store_count: int = Field(ge=0)
    confidence: int = Field(ge=0, le=100)


class CompetitorsResponse(BaseModel):
    category: Category | None = None
    category_median_etb: float | None = None
    items: list[CompetitorRow]


class SourceEconomics(BaseModel):
    source_type: str
    observations: int
    verified_observations: int
    prompt_tokens: float
    candidates_tokens: float
    total_tokens: float
    gemini_cost_etb: float
    cost_per_verified_observation_etb: float | None = None


class CostBenchmark(BaseModel):
    id: str
    label: str
    min_etb: float
    max_etb: float
    unit: str = Field(description="What one unit of this benchmark buys.")
    source: str


class UnitEconomicsResponse(BaseModel):
    period_days: int
    observations: int
    verified_observations: int
    prompt_tokens: float
    candidates_tokens: float
    total_tokens: float
    gemini_cost_usd: float
    gemini_cost_etb: float
    cost_per_verified_observation_etb: float | None = None
    usd_to_etb: float
    gemini_input_usd_per_mtok: float
    gemini_output_usd_per_mtok: float
    by_source: list[SourceEconomics]
    benchmarks: list[CostBenchmark]
