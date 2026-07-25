from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


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

