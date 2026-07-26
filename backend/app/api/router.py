import csv
import io
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.deps import RATE_LIMIT_RESPONSES, DeviceIdHeader, RateLimited, SessionDep
from app.api.uploads import UPLOAD_RESPONSES, read_image
from app.config import get_settings
from app.fixtures import load_fixture
from app.repositories import (
    load_competitors,
    load_compliance,
    load_districts,
    load_evidence_log,
    load_nearby_stores,
    load_oos_alerts,
    load_product_detail,
    load_pulse,
    load_store_detail,
    load_trends,
    load_unit_economics,
    market_insights_csv_rows,
    search_products,
)
from app.schemas.analytics import (
    CompetitorsResponse,
    ComplianceResponse,
    DistrictsResponse,
    OosResponse,
    TrendsResponse,
    UnitEconomicsResponse,
)
from app.schemas.common import Category, ErrorResponse, EvidenceStatus, HealthResponse
from app.schemas.evidence import (
    EvidenceLogResponse,
    ManualEvidenceRequest,
    ManualEvidenceResponse,
    OosEvidenceRequest,
    OosEvidenceResponse,
    PriceListUploadResponse,
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
from app.services.ingest import (
    MissingReference,
    identify_from_image,
    ingest_manual_report,
    ingest_oos_report,
    ingest_price_list,
    ingest_receipt,
    ingest_shelf_tag,
)
from app.services.ocr import ExtractionError

router = APIRouter()

WRITE_RESPONSES = {**RATE_LIMIT_RESPONSES, **UPLOAD_RESPONSES}

PRODUCT_FIXTURES = {
    UUID("11111111-1111-4111-8111-111111111111"): "product_high_confidence.json",
    UUID("33333333-3333-4333-8333-333333333333"): "product_low_confidence.json",
}

PRODUCT_NOT_FOUND = "Product not found"
STORE_NOT_FOUND = "Store not found"


def not_found(when: str) -> dict[int | str, dict[str, Any]]:
    """Document a 404 the frontend has to render, rather than leaving it a surprise."""
    return {status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": when}}


@contextmanager
def _extraction_errors() -> Iterator[None]:
    """A Gemini failure is the upstream's fault, so it answers 502, not 500."""
    try:
        yield
    except ExtractionError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"The image could not be read: {error}",
        ) from error


@router.get("/healthz", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        fixtures=get_settings().use_fixtures,
        checked_at=datetime.now(timezone.utc),
    )


@router.get("/api/pulse", response_model=PulseResponse, tags=["market"])
async def get_pulse(session: SessionDep) -> PulseResponse:
    if session is None:
        return PulseResponse.model_validate(load_fixture("pulse.json"))
    return await load_pulse(session)


@router.get("/api/products", response_model=ProductListResponse, tags=["products"])
async def list_products(
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    category: Category | None = None,
    brand: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProductListResponse:
    if session is not None:
        return await search_products(
            session,
            query=q,
            category=category,
            brand=brand,
            limit=limit,
            offset=offset,
        )

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
    if brand:
        needle = brand.casefold()
        items = [item for item in items if item.brand.casefold() == needle]

    return ProductListResponse(
        total=len(items),
        limit=limit,
        offset=offset,
        items=items[offset : offset + limit],
    )


@router.get(
    "/api/products/{product_id}",
    response_model=ProductDetail,
    tags=["products"],
    responses=not_found("No product with this id has a priced estimate."),
)
async def get_product(product_id: UUID, session: SessionDep) -> ProductDetail:
    if session is not None:
        detail = await load_product_detail(session, product_id)
        if detail is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCT_NOT_FOUND)
        return detail

    fixture_name = PRODUCT_FIXTURES.get(product_id)
    if fixture_name is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCT_NOT_FOUND)
    return ProductDetail.model_validate(load_fixture(fixture_name))


@router.get(
    "/api/products/{product_id}/stores",
    response_model=NearbyStoresResponse,
    tags=["products"],
    responses=not_found("No product with this id has a priced estimate."),
)
async def list_product_stores(
    product_id: UUID,
    session: SessionDep,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_m: Annotated[int, Query(ge=100, le=50_000)] = 5_000,
) -> NearbyStoresResponse:
    if session is not None:
        nearby = await load_nearby_stores(
            session,
            product_id,
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_m,
        )
        if nearby is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCT_NOT_FOUND)
        return nearby

    result = NearbyStoresResponse.model_validate(load_fixture("nearby_stores.json"))
    if product_id != result.product_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCT_NOT_FOUND)
    result.items = [
        item for item in result.items if item.distance_m is None or item.distance_m <= radius_m
    ]
    return result


@router.get(
    "/api/stores/{store_id}",
    response_model=StoreDetail,
    tags=["stores"],
    responses=not_found("No store with this id."),
)
async def get_store(store_id: UUID, session: SessionDep) -> StoreDetail:
    if session is not None:
        store = await load_store_detail(session, store_id)
        if store is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=STORE_NOT_FOUND)
        return store

    result = StoreDetail.model_validate(load_fixture("store.json"))
    if store_id != result.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=STORE_NOT_FOUND)
    return result


@router.get("/api/evidence", response_model=EvidenceLogResponse, tags=["evidence"])
async def list_evidence(
    session: SessionDep,
    evidence_status: Annotated[
        EvidenceStatus | None,
        Query(alias="status", description="Filter by the gate decision."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EvidenceLogResponse:
    if session is not None:
        return await load_evidence_log(
            session,
            status=evidence_status,
            limit=limit,
            offset=offset,
        )

    fixture = EvidenceLogResponse.model_validate(load_fixture("evidence_log.json"))
    items = fixture.items

    if evidence_status:
        items = [item for item in items if item.status == evidence_status]

    return EvidenceLogResponse(
        total=len(items),
        limit=limit,
        offset=offset,
        items=items[offset : offset + limit],
    )


@router.post(
    "/api/evidence/receipt",
    response_model=ReceiptUploadResponse,
    tags=["evidence"],
    dependencies=[RateLimited],
    responses=WRITE_RESPONSES,
)
async def upload_receipt(
    image: Annotated[UploadFile, File(description="JPEG, PNG, or WebP receipt image.")],
    session: SessionDep,
    device_id: DeviceIdHeader = None,
) -> ReceiptUploadResponse:
    if session is None:
        return ReceiptUploadResponse.model_validate(load_fixture("receipt_upload.json"))

    photo = await read_image(image)
    with _extraction_errors():
        response = await ingest_receipt(session, photo, device_id=device_id)
    await session.commit()
    return response


@router.post(
    "/api/evidence/price-list",
    response_model=PriceListUploadResponse,
    tags=["evidence"],
    dependencies=[RateLimited],
    responses={
        **WRITE_RESPONSES,
        **not_found("The report names a store that does not exist."),
    },
)
async def upload_price_list(
    image: Annotated[UploadFile, File(description="JPEG, PNG, or WebP posted price-list image.")],
    store_id: Annotated[UUID, Form(description="Store where the price list was photographed.")],
    session: SessionDep,
    device_id: DeviceIdHeader = None,
) -> PriceListUploadResponse:
    if session is None:
        return PriceListUploadResponse.model_validate(load_fixture("price_list_upload.json"))

    photo = await read_image(image)
    with _extraction_errors():
        try:
            response = await ingest_price_list(
                session, photo, store_id=store_id, device_id=device_id
            )
        except MissingReference as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
            ) from error
    await session.commit()
    return response


@router.post(
    "/api/evidence/shelf",
    response_model=ShelfUploadResponse,
    tags=["evidence"],
    dependencies=[RateLimited],
    responses={
        **WRITE_RESPONSES,
        **not_found("The tagged product is not in the catalog, so its price cannot be recorded."),
    },
)
async def upload_shelf_photo(
    image: Annotated[UploadFile, File(description="JPEG, PNG, or WebP shelf photo.")],
    session: SessionDep,
    device_id: DeviceIdHeader = None,
) -> ShelfUploadResponse:
    if session is None:
        return ShelfUploadResponse.model_validate(load_fixture("shelf_upload.json"))

    photo = await read_image(image)
    with _extraction_errors():
        try:
            response = await ingest_shelf_tag(session, photo, device_id=device_id)
        except MissingReference as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
            ) from error
    await session.commit()
    return response


@router.post(
    "/api/evidence/manual",
    response_model=ManualEvidenceResponse,
    tags=["evidence"],
    dependencies=[RateLimited],
    responses={
        **RATE_LIMIT_RESPONSES,
        **not_found("The report names a product or store that does not exist."),
    },
)
async def submit_manual_evidence(
    payload: ManualEvidenceRequest,
    session: SessionDep,
    device_id: DeviceIdHeader = None,
) -> ManualEvidenceResponse:
    if session is None:
        return ManualEvidenceResponse.model_validate(load_fixture("manual_evidence.json"))

    try:
        response = await ingest_manual_report(session, payload, device_id=device_id)
    except MissingReference as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    await session.commit()
    return response


@router.post(
    "/api/evidence/oos",
    response_model=OosEvidenceResponse,
    tags=["evidence"],
    dependencies=[RateLimited],
    responses={
        **RATE_LIMIT_RESPONSES,
        **not_found("The report names a product or store that does not exist."),
    },
)
async def submit_oos_evidence(
    payload: OosEvidenceRequest,
    session: SessionDep,
    device_id: DeviceIdHeader = None,
) -> OosEvidenceResponse:
    if session is None:
        return OosEvidenceResponse.model_validate(load_fixture("oos_evidence.json"))

    try:
        response = await ingest_oos_report(session, payload, device_id=device_id)
    except MissingReference as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    await session.commit()
    return response


@router.post(
    "/api/scan/identify",
    response_model=ProductIdentification,
    tags=["scan"],
    dependencies=[RateLimited],
    responses=WRITE_RESPONSES,
)
async def identify_product(
    image: Annotated[UploadFile, File(description="JPEG, PNG, or WebP product image.")],
    session: SessionDep,
) -> ProductIdentification:
    if session is None:
        return ProductIdentification.model_validate(load_fixture("product_identification.json"))

    photo = await read_image(image)
    with _extraction_errors():
        identification = await identify_from_image(session, photo)
    # Matching can teach the catalog a new alias, which is worth keeping.
    await session.commit()
    return identification


@router.get("/api/analytics/trends", response_model=TrendsResponse, tags=["analytics"])
async def get_trends(
    session: SessionDep,
    period_days: Annotated[int, Query(ge=2, le=90)] = 7,
    category: Category | None = None,
) -> TrendsResponse:
    if session is not None:
        return await load_trends(session, period_days=period_days, category=category)

    result = TrendsResponse.model_validate(load_fixture("trends.json"))
    result.period_days = period_days
    if category:
        # Fixture trends lack category tags; keep the demo chart intact.
        pass
    return result


@router.get(
    "/api/analytics/unit-economics",
    response_model=UnitEconomicsResponse,
    tags=["analytics"],
)
async def get_unit_economics(
    session: SessionDep,
    period_days: Annotated[int, Query(ge=1, le=90)] = 30,
) -> UnitEconomicsResponse:
    if session is not None:
        return await load_unit_economics(session, period_days=period_days)

    result = UnitEconomicsResponse.model_validate(load_fixture("unit_economics.json"))
    result.period_days = period_days
    return result


@router.get(
    "/api/analytics/compliance",
    response_model=ComplianceResponse,
    tags=["analytics"],
)
async def get_compliance(
    session: SessionDep,
    category: Category | None = None,
    brand: Annotated[str | None, Query(max_length=100)] = None,
) -> ComplianceResponse:
    if session is not None:
        return await load_compliance(session, category=category, brand=brand)
    return ComplianceResponse.model_validate(load_fixture("compliance.json"))


@router.get(
    "/api/analytics/districts",
    response_model=DistrictsResponse,
    tags=["analytics"],
)
async def get_districts(
    session: SessionDep,
    category: Category | None = None,
    product_id: UUID | None = None,
) -> DistrictsResponse:
    if session is not None:
        return await load_districts(session, category=category, product_id=product_id)
    return DistrictsResponse.model_validate(load_fixture("districts.json"))


@router.get("/api/analytics/oos", response_model=OosResponse, tags=["analytics"])
async def get_oos_alerts(
    session: SessionDep,
    category: Category | None = None,
    days: Annotated[int, Query(ge=1, le=90)] = 7,
) -> OosResponse:
    if session is not None:
        return await load_oos_alerts(session, category=category, days=days)
    result = OosResponse.model_validate(load_fixture("oos.json"))
    result.period_days = days
    return result


@router.get(
    "/api/analytics/competitors",
    response_model=CompetitorsResponse,
    tags=["analytics"],
)
async def get_competitors(
    session: SessionDep,
    category: Category | None = None,
) -> CompetitorsResponse:
    if session is not None:
        return await load_competitors(session, category=category)
    return CompetitorsResponse.model_validate(load_fixture("competitors.json"))


@router.get("/api/exports/market-insights.csv", tags=["exports"])
async def export_market_insights(
    session: SessionDep,
    category: Category | None = None,
    brand: Annotated[str | None, Query(max_length=100)] = None,
    level: Annotated[Literal["district", "store"], Query()] = "district",
) -> StreamingResponse:
    if session is None:
        rows = load_fixture("market_insights_export.json")["rows"]
    else:
        rows = await market_insights_csv_rows(
            session,
            category=category,
            brand=brand,
            level=level,
        )

    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    else:
        buffer.write("product,brand,category\n")

    buffer.seek(0)
    filename = f"suqcheck-market-insights-{level}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

