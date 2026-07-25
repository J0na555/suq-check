from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Header, HTTPException, Query, UploadFile, status

from app.config import get_settings
from app.fixtures import load_fixture
from app.schemas.analytics import TrendsResponse
from app.schemas.common import Category, HealthResponse
from app.schemas.evidence import (
    ManualEvidenceRequest,
    ManualEvidenceResponse,
    ProductIdentification,
    ReceiptUploadResponse,
    ShelfUploadResponse,
)
from app.schemas.products import (
    NearbyStoresResponse,
    ProductDetail,
    ProductListResponse,
    StoreDetail,
)
from app.schemas.pulse import PulseResponse

router = APIRouter()

PRODUCT_FIXTURES = {
    UUID("11111111-1111-4111-8111-111111111111"): "product_high_confidence.json",
    UUID("33333333-3333-4333-8333-333333333333"): "product_low_confidence.json",
}


@router.get("/healthz", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        fixtures=get_settings().use_fixtures,
        checked_at=datetime.now(timezone.utc),
    )


@router.get("/api/pulse", response_model=PulseResponse, tags=["market"])
async def get_pulse() -> PulseResponse:
    return PulseResponse.model_validate(load_fixture("pulse.json"))


@router.get("/api/products", response_model=ProductListResponse, tags=["products"])
async def list_products(
    q: Annotated[str | None, Query(max_length=100)] = None,
    category: Category | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProductListResponse:
    fixture = ProductListResponse.model_validate(load_fixture("products.json"))
    items = fixture.items

    if q:
        query = q.casefold()
        items = [
            item
            for item in items
            if query in item.canonical_name.casefold() or query in item.brand.casefold()
        ]
    if category:
        items = [item for item in items if item.category == category]

    return ProductListResponse(
        total=len(items),
        limit=limit,
        offset=offset,
        items=items[offset : offset + limit],
    )


@router.get("/api/products/{product_id}", response_model=ProductDetail, tags=["products"])
async def get_product(product_id: UUID) -> ProductDetail:
    fixture_name = PRODUCT_FIXTURES.get(product_id)
    if fixture_name is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return ProductDetail.model_validate(load_fixture(fixture_name))


@router.get(
    "/api/products/{product_id}/stores",
    response_model=NearbyStoresResponse,
    tags=["products"],
)
async def list_product_stores(
    product_id: UUID,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_m: Annotated[int, Query(ge=100, le=50_000)] = 5_000,
) -> NearbyStoresResponse:
    del latitude, longitude
    result = NearbyStoresResponse.model_validate(load_fixture("nearby_stores.json"))
    if product_id != result.product_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    result.items = [
        item for item in result.items if item.distance_m is None or item.distance_m <= radius_m
    ]
    return result


@router.get("/api/stores/{store_id}", response_model=StoreDetail, tags=["stores"])
async def get_store(store_id: UUID) -> StoreDetail:
    result = StoreDetail.model_validate(load_fixture("store.json"))
    if store_id != result.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return result


@router.post(
    "/api/evidence/receipt",
    response_model=ReceiptUploadResponse,
    tags=["evidence"],
)
async def upload_receipt(
    image: Annotated[UploadFile, File(description="JPEG, PNG, or WebP receipt image.")],
    device_id: Annotated[str | None, Header(alias="X-Device-Id")] = None,
) -> ReceiptUploadResponse:
    del image, device_id
    return ReceiptUploadResponse.model_validate(load_fixture("receipt_upload.json"))


@router.post(
    "/api/evidence/shelf",
    response_model=ShelfUploadResponse,
    tags=["evidence"],
)
async def upload_shelf_photo(
    image: Annotated[UploadFile, File(description="JPEG, PNG, or WebP shelf photo.")],
    device_id: Annotated[str | None, Header(alias="X-Device-Id")] = None,
) -> ShelfUploadResponse:
    del image, device_id
    return ShelfUploadResponse.model_validate(load_fixture("shelf_upload.json"))


@router.post(
    "/api/evidence/manual",
    response_model=ManualEvidenceResponse,
    tags=["evidence"],
)
async def submit_manual_evidence(
    payload: ManualEvidenceRequest,
    device_id: Annotated[str | None, Header(alias="X-Device-Id")] = None,
) -> ManualEvidenceResponse:
    del payload, device_id
    return ManualEvidenceResponse.model_validate(load_fixture("manual_evidence.json"))


@router.post(
    "/api/scan/identify",
    response_model=ProductIdentification,
    tags=["scan"],
)
async def identify_product(
    image: Annotated[UploadFile, File(description="JPEG, PNG, or WebP product image.")],
) -> ProductIdentification:
    del image
    return ProductIdentification.model_validate(load_fixture("product_identification.json"))


@router.get("/api/analytics/trends", response_model=TrendsResponse, tags=["analytics"])
async def get_trends(
    period_days: Annotated[int, Query(ge=2, le=90)] = 7,
) -> TrendsResponse:
    result = TrendsResponse.model_validate(load_fixture("trends.json"))
    result.period_days = period_days
    return result

