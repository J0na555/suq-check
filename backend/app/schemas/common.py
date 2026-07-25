from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

Category = Literal[
    "cooking_oil",
    "sugar",
    "rice",
    "flour",
    "salt",
    "pasta",
    "coffee",
    "tea",
    "milk",
    "soap",
    "detergent",
    "toothpaste",
    "shampoo",
    "bottled_water",
]
ConfidenceBand = Literal["high", "medium", "low"]
EvidenceStatus = Literal["accepted", "pending", "rejected"]
SourceType = Literal[
    "partner",
    "receipt",
    "scrape",
    "store_visit",
    "shelf_photo",
    "community",
]


class ConfidenceFactor(BaseModel):
    name: Literal["volume", "agreement", "freshness", "diversity"]
    score: float = Field(ge=0, le=1)
    weight: float = Field(ge=0, le=1)
    detail: str


class ConfidenceBreakdown(BaseModel):
    score: int = Field(ge=0, le=100)
    band: ConfidenceBand
    factors: list[ConfidenceFactor]
    capped: bool = False
    cap_reason: str | None = None


class SourceSummary(BaseModel):
    source_type: SourceType
    label: str
    count: int = Field(ge=0)
    newest_observed_at: datetime


class HistoryPoint(BaseModel):
    day: date
    price_etb: float = Field(gt=0)
    evidence_count: int = Field(ge=0)


class StoreSummary(BaseModel):
    id: UUID
    name: str
    district: str
    kind: Literal["supermarket", "shop", "online"]
    latitude: float
    longitude: float


class Pagination(BaseModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class HealthResponse(BaseModel):
    status: Literal["ok"]
    fixtures: bool
    checked_at: datetime

