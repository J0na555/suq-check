from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PulseMetrics(BaseModel):
    verified_prices_today: int = Field(ge=0)
    products_covered: int = Field(ge=0)
    stores_reporting: int = Field(ge=0)
    new_receipts_today: int = Field(ge=0)
    average_confidence: int = Field(ge=0, le=100)
    mrp_compliance_pct: float = Field(ge=0, le=100)
    oos_rate_pct: float = Field(ge=0, le=100)
    categories_covered: int = Field(ge=0)
    active_oos_alerts: int = Field(ge=0)


class PulseMover(BaseModel):
    product_id: UUID
    product_name: str
    kind: Literal["fastest_rising", "largest_drop", "most_stable", "most_verified"]
    value: float
    display_value: str


class PulseResponse(BaseModel):
    metrics: PulseMetrics
    movers: list[PulseMover]
    cheapest_district: str
    most_active_store: str
