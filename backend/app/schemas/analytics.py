from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


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
