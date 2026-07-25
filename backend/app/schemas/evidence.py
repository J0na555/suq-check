from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import Category, EvidenceStatus, Pagination, SourceType


class ExtractedLineItem(BaseModel):
    raw_text: str
    quantity: float = Field(default=1, gt=0)
    unit_price_etb: float = Field(gt=0)
    total_price_etb: float = Field(gt=0)
    matched_product_id: UUID | None = None
    matched_product_name: str | None = None
    match_confidence: float = Field(ge=0, le=1)


class ReceiptExtraction(BaseModel):
    store_name: str | None = None
    observed_on: date | None = None
    total_etb: float | None = Field(default=None, gt=0)
    ocr_confidence: float = Field(ge=0, le=1)
    items: list[ExtractedLineItem]


class ShelfExtraction(BaseModel):
    raw_product_text: str
    price_etb: float = Field(gt=0)
    matched_product_id: UUID | None = None
    matched_product_name: str | None = None
    ocr_confidence: float = Field(ge=0, le=1)
    match_confidence: float = Field(ge=0, le=1)


class EvidenceDecision(BaseModel):
    id: UUID
    product_id: UUID | None = None
    product_name: str
    price_etb: float = Field(gt=0)
    source_type: SourceType
    status: EvidenceStatus
    reason: str


class ReceiptUploadResponse(BaseModel):
    extraction: ReceiptExtraction
    decisions: list[EvidenceDecision]


class PriceListExtraction(BaseModel):
    store_id: UUID
    store_name: str
    observed_on: date | None = None
    ocr_confidence: float = Field(ge=0, le=1)
    items: list[ExtractedLineItem]


class PriceListUploadResponse(BaseModel):
    extraction: PriceListExtraction
    decisions: list[EvidenceDecision]


class ShelfUploadResponse(BaseModel):
    extraction: ShelfExtraction
    decision: EvidenceDecision


class ManualEvidenceRequest(BaseModel):
    product_id: UUID
    store_id: UUID
    price_etb: float = Field(gt=0)
    observed_at: datetime
    source_type: Literal["store_visit", "community"] = "community"


class ManualEvidenceResponse(BaseModel):
    decision: EvidenceDecision


class EvidenceLogItem(BaseModel):
    id: UUID
    product_name: str
    store_name: str | None = None
    price_etb: float = Field(gt=0)
    source_type: SourceType
    status: EvidenceStatus
    rejection_reason: str | None = None
    observed_at: datetime
    created_at: datetime


class EvidenceLogResponse(Pagination):
    items: list[EvidenceLogItem]


class ProductIdentification(BaseModel):
    product_id: UUID | None = None
    canonical_name: str
    brand: str
    category: Category
    size_value: float = Field(gt=0)
    size_unit: Literal["ml", "l", "g", "kg", "piece"]
    confidence: float = Field(ge=0, le=1)
    match_method: Literal["alias_exact", "trigram", "gemini", "gemini_vision", "new_product"]

