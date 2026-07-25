"""The write path end to end, with Gemini replaced by a stub.

Nothing here calls Gemini: the extraction functions are the seam, so every test
supplies the text a receipt or tag would have produced and checks what the
normalizer, the gate, and the engine did with it.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Evidence, PriceEstimate, Product, ProductAlias
from app.models.enums import EvidenceSource, EvidenceStatus
from app.schemas.evidence import ManualEvidenceRequest
from app.seed import read_products, read_stores
from app.services import ingest, normalize, rate_limit
from app.services.ocr import (
    CatalogChoice,
    ExtractionError,
    IdentifiedProduct,
    PriceListDocument,
    PriceListLine,
    ReceiptDocument,
    ReceiptLine,
    ShelfTag,
)

PRODUCTS = {product.canonical_name: product for product in read_products()}
STORES = {store.name: store for store in read_stores()}

OIL = PRODUCTS["Hayat Cooking Oil 1L"]
SUGAR = PRODUCTS["Shega White Sugar 1kg"]
# Thin coverage stays out of the weekly visit pass, so one receipt can still
# move the market estimate instead of drowning in thousands of visit rows.
THIN = PRODUCTS["San Marco Pasta 500g"]
SELAM_MART = STORES["Selam Mart"]

JPEG = ("receipt.jpg", b"not-really-an-image", "image/jpeg")
DEVICE = {"X-Device-Id": "test-device"}


def receipt(*lines: tuple[str, float], store_name: str | None = "Selam Mart") -> ReceiptDocument:
    return ReceiptDocument(
        store_name=store_name,
        observed_on=None,
        total_etb=sum(price for _, price in lines),
        ocr_confidence=0.95,
        items=[
            ReceiptLine(
                raw_text=text,
                quantity=1,
                unit_price_etb=price,
                total_price_etb=price,
            )
            for text, price in lines
        ],
    )


@pytest.fixture
def gemini_receipt(monkeypatch: pytest.MonkeyPatch):
    """Replace receipt extraction with a canned document."""

    def use(document: ReceiptDocument) -> None:
        async def fake(image: bytes, mime_type: str = "image/jpeg") -> ReceiptDocument:
            del image, mime_type
            return document

        monkeypatch.setattr(ingest, "extract_receipt", fake)

    return use


@pytest.fixture
def gemini_shelf_tag(monkeypatch: pytest.MonkeyPatch):
    def use(tag: ShelfTag) -> None:
        async def fake(image: bytes, mime_type: str = "image/jpeg") -> ShelfTag:
            del image, mime_type
            return tag

        monkeypatch.setattr(ingest, "extract_shelf_tag", fake)

    return use


@pytest.fixture
def gemini_price_list(monkeypatch: pytest.MonkeyPatch):
    def use(document: PriceListDocument) -> None:
        async def fake(image: bytes, mime_type: str = "image/jpeg") -> PriceListDocument:
            del image, mime_type
            return document

        monkeypatch.setattr(ingest, "extract_price_list", fake)

    return use


@pytest.fixture
def gemini_vision(monkeypatch: pytest.MonkeyPatch):
    def use(seen: IdentifiedProduct) -> None:
        async def fake(image: bytes, mime_type: str = "image/jpeg") -> IdentifiedProduct:
            del image, mime_type
            return seen

        monkeypatch.setattr(ingest, "identify_product", fake)

    return use


async def _market_price(session: AsyncSession, product_id) -> float:
    price = await session.scalar(
        select(PriceEstimate.price_etb).where(
            PriceEstimate.product_id == product_id,
            PriceEstimate.store_id.is_(None),
        )
    )
    return float(price)


@pytest.mark.asyncio
async def test_receipt_line_matching_the_catalog_exactly_is_accepted(
    writing_client: TestClient,
    writable_session: AsyncSession,
    gemini_receipt,
) -> None:
    market = await _market_price(writable_session, OIL.id)
    gemini_receipt(receipt((OIL.canonical_name, round(market, 2))))

    response = writing_client.post("/api/evidence/receipt", files={"image": JPEG}, headers=DEVICE)

    assert response.status_code == 200
    body = response.json()
    assert body["extraction"]["store_name"] == SELAM_MART.name
    item = body["extraction"]["items"][0]
    assert item["matched_product_id"] == str(OIL.id)
    assert item["match_confidence"] == 1.0
    decision = body["decisions"][0]
    assert decision["status"] == "accepted"
    assert decision["product_name"] == OIL.canonical_name
    assert "agrees with" in decision["reason"]


@pytest.mark.asyncio
async def test_a_wildly_low_receipt_price_lands_in_pending(
    writing_client: TestClient,
    writable_session: AsyncSession,
    gemini_receipt,
) -> None:
    market = await _market_price(writable_session, OIL.id)
    gemini_receipt(receipt((OIL.canonical_name, round(market * 0.35, 2))))

    response = writing_client.post("/api/evidence/receipt", files={"image": JPEG}, headers=DEVICE)

    decision = response.json()["decisions"][0]
    assert decision["status"] == "pending"
    assert "needs verification" in decision["reason"]

    logged = writing_client.get("/api/evidence", params={"status": "pending"}).json()
    assert decision["id"] in {item["id"] for item in logged["items"]}


@pytest.mark.asyncio
async def test_a_shouted_receipt_line_matches_by_trigram_then_by_alias(
    writing_client: TestClient,
    writable_session: AsyncSession,
    gemini_receipt,
) -> None:
    market = await _market_price(writable_session, OIL.id)
    gemini_receipt(receipt(("HAYAT OIL 1L", round(market, 2))))

    first = writing_client.post("/api/evidence/receipt", files={"image": JPEG}, headers=DEVICE)
    second = writing_client.post("/api/evidence/receipt", files={"image": JPEG}, headers=DEVICE)

    first_item = first.json()["extraction"]["items"][0]
    second_item = second.json()["extraction"]["items"][0]
    assert first_item["matched_product_id"] == str(OIL.id)
    assert 0.55 <= first_item["match_confidence"] < 1.0
    # The write-back turned a fuzzy match into an exact one.
    assert second_item["match_confidence"] == 1.0

    learned = await writable_session.scalar(
        select(func.count())
        .select_from(ProductAlias)
        .where(ProductAlias.normalized_text == "hayat oil 1l")
    )
    assert learned == 1


@pytest.mark.asyncio
async def test_an_unknown_receipt_line_is_reported_but_not_stored(
    writing_client: TestClient,
    writable_session: AsyncSession,
    gemini_receipt,
) -> None:
    before = await writable_session.scalar(select(func.count()).select_from(Evidence))
    gemini_receipt(receipt(("ZAMBEZI FLOOR POLISH 4L", 260.0)))

    response = writing_client.post("/api/evidence/receipt", files={"image": JPEG}, headers=DEVICE)

    body = response.json()
    assert body["extraction"]["items"][0]["matched_product_id"] is None
    assert body["decisions"] == []
    writable_session.expire_all()
    assert await writable_session.scalar(select(func.count()).select_from(Evidence)) == before


@pytest.mark.asyncio
async def test_accepted_evidence_moves_the_estimate_and_keeps_the_thumbnail(
    writing_client: TestClient,
    writable_session: AsyncSession,
    gemini_receipt,
) -> None:
    before = await _market_price(writable_session, THIN.id)
    gemini_receipt(receipt((THIN.canonical_name, round(before * 1.2, 2))))

    response = writing_client.post("/api/evidence/receipt", files={"image": JPEG}, headers=DEVICE)
    assert response.json()["decisions"][0]["status"] == "accepted"

    writable_session.expire_all()
    after = await _market_price(writable_session, THIN.id)
    assert after > before

    stored = await writable_session.scalar(
        select(Evidence)
        .where(Evidence.product_id == THIN.id, Evidence.source_type == EvidenceSource.RECEIPT)
        .order_by(Evidence.created_at.desc())
    )
    assert stored.raw_payload["device_id"] == DEVICE["X-Device-Id"]
    # The stub upload is not a real image, so there is nothing to shrink.
    assert stored.thumbnail is None


def price_list(*lines: tuple[str, float]) -> PriceListDocument:
    return PriceListDocument(
        store_name=None,
        observed_on=None,
        ocr_confidence=0.94,
        items=[PriceListLine(raw_text=text, price_etb=price) for text, price in lines],
    )


@pytest.mark.asyncio
async def test_price_list_lines_become_store_visit_evidence(
    writing_client: TestClient,
    writable_session: AsyncSession,
    gemini_price_list,
) -> None:
    market = await _market_price(writable_session, OIL.id)
    gemini_price_list(price_list((OIL.canonical_name, round(market, 2))))

    response = writing_client.post(
        "/api/evidence/price-list",
        files={"image": JPEG},
        data={"store_id": str(SELAM_MART.id)},
        headers=DEVICE,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["extraction"]["store_id"] == str(SELAM_MART.id)
    assert body["extraction"]["store_name"] == SELAM_MART.name
    item = body["extraction"]["items"][0]
    assert item["matched_product_id"] == str(OIL.id)
    assert item["quantity"] == 1
    decision = body["decisions"][0]
    assert decision["source_type"] == "store_visit"
    assert decision["status"] == "accepted"

    stored = await writable_session.scalar(
        select(Evidence)
        .where(
            Evidence.product_id == OIL.id,
            Evidence.source_type == EvidenceSource.STORE_VISIT,
            Evidence.store_id == SELAM_MART.id,
        )
        .order_by(Evidence.created_at.desc())
    )
    assert stored is not None
    assert stored.raw_payload["device_id"] == DEVICE["X-Device-Id"]


@pytest.mark.asyncio
async def test_an_unknown_price_list_line_is_reported_but_not_stored(
    writing_client: TestClient,
    writable_session: AsyncSession,
    gemini_price_list,
) -> None:
    before = await writable_session.scalar(select(func.count()).select_from(Evidence))
    gemini_price_list(price_list(("ZAMBEZI FLOOR POLISH 4L", 260.0)))

    response = writing_client.post(
        "/api/evidence/price-list",
        files={"image": JPEG},
        data={"store_id": str(SELAM_MART.id)},
        headers=DEVICE,
    )

    body = response.json()
    assert body["extraction"]["items"][0]["matched_product_id"] is None
    assert body["decisions"] == []
    writable_session.expire_all()
    assert await writable_session.scalar(select(func.count()).select_from(Evidence)) == before


def test_price_list_for_an_unknown_store_is_404(
    writing_client: TestClient,
    gemini_price_list,
) -> None:
    gemini_price_list(price_list((OIL.canonical_name, 340.0)))

    response = writing_client.post(
        "/api/evidence/price-list",
        files={"image": JPEG},
        data={"store_id": "44444444-4444-4444-8444-444444444444"},
        headers=DEVICE,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Store not found"


@pytest.mark.asyncio
async def test_shelf_tag_becomes_a_shelf_photo_report(
    writing_client: TestClient,
    writable_session: AsyncSession,
    gemini_shelf_tag,
) -> None:
    market = await _market_price(writable_session, OIL.id)
    # `1000ML` has to unify to `1l` for this to match the seeded alias at all.
    gemini_shelf_tag(
        ShelfTag(
            raw_product_text="HAYAT COOKING OIL 1000ML",
            price_etb=round(market * 1.1, 2),
            ocr_confidence=0.9,
        )
    )

    response = writing_client.post("/api/evidence/shelf", files={"image": JPEG}, headers=DEVICE)

    assert response.status_code == 200
    body = response.json()
    assert body["extraction"]["matched_product_id"] == str(OIL.id)
    assert body["extraction"]["match_confidence"] == 1.0
    assert body["decision"]["source_type"] == "shelf_photo"
    assert body["decision"]["status"] == "accepted"


@pytest.mark.asyncio
async def test_a_shelf_tag_for_something_uncatalogued_is_404(
    writing_client: TestClient,
    gemini_shelf_tag,
) -> None:
    gemini_shelf_tag(
        ShelfTag(raw_product_text="Zambezi Floor Polish 4L", price_etb=260, ocr_confidence=0.9)
    )

    response = writing_client.post("/api/evidence/shelf", files={"image": JPEG}, headers=DEVICE)

    assert response.status_code == 404
    assert "not in the catalog" in response.json()["detail"]


@pytest.mark.asyncio
async def test_manual_report_of_the_demo_outlier_pends(
    writing_client: TestClient,
    writable_session: AsyncSession,
) -> None:
    market = await _market_price(writable_session, OIL.id)
    response = writing_client.post(
        "/api/evidence/manual",
        json={
            "product_id": str(OIL.id),
            "store_id": str(SELAM_MART.id),
            "price_etb": round(market * 0.35, 2),
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "source_type": "community",
        },
        headers=DEVICE,
    )

    assert response.status_code == 200
    decision = response.json()["decision"]
    assert decision["status"] == "pending"
    assert decision["source_type"] == "community"


def test_manual_report_for_an_unknown_product_is_404(writing_client: TestClient) -> None:
    response = writing_client.post(
        "/api/evidence/manual",
        json={
            "product_id": "44444444-4444-4444-8444-444444444444",
            "store_id": str(SELAM_MART.id),
            "price_etb": 340,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "source_type": "community",
        },
        headers=DEVICE,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


@pytest.mark.asyncio
async def test_a_future_timestamp_is_pulled_back_to_now(
    writable_session: AsyncSession,
) -> None:
    now = datetime.now(timezone.utc)
    product = await writable_session.get(Product, OIL.id)
    market = await _market_price(writable_session, OIL.id)
    request = ManualEvidenceRequest(
        product_id=product.id,
        store_id=SELAM_MART.id,
        price_etb=round(market, 2),
        observed_at=now + timedelta(days=3),
        source_type="store_visit",
    )

    response = await ingest.ingest_manual_report(writable_session, request, now=now)

    stored = await writable_session.get(Evidence, response.decision.id)
    assert stored.observed_at.replace(tzinfo=timezone.utc) <= now


@pytest.mark.asyncio
async def test_scan_identifies_a_catalog_product(
    writing_client: TestClient,
    gemini_vision,
) -> None:
    gemini_vision(
        IdentifiedProduct(
            canonical_name="Hayat Cooking Oil 1L",
            brand="Hayat",
            category="cooking_oil",
            size_value=1,
            size_unit="l",
            confidence=0.96,
        )
    )

    response = writing_client.post("/api/scan/identify", files={"image": JPEG})

    assert response.status_code == 200
    body = response.json()
    assert body["product_id"] == str(OIL.id)
    assert body["match_method"] == "alias_exact"
    assert body["size_unit"] == "l"


@pytest.mark.asyncio
async def test_scan_reports_something_not_in_the_catalog(
    writing_client: TestClient,
    gemini_vision,
) -> None:
    gemini_vision(
        IdentifiedProduct(
            canonical_name="Zambezi Floor Polish 4L",
            brand="Zambezi",
            category="detergent",
            size_value=4,
            size_unit="l",
            confidence=0.71,
        )
    )

    response = writing_client.post("/api/scan/identify", files={"image": JPEG})

    assert response.status_code == 200
    body = response.json()
    assert body["product_id"] is None
    assert body["match_method"] == "gemini_vision"
    assert body["canonical_name"] == "Zambezi Floor Polish 4L"


def test_a_gemini_failure_answers_502(
    writing_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail(image: bytes, mime_type: str = "image/jpeg") -> ReceiptDocument:
        del image, mime_type
        raise ExtractionError("GEMINI_API_KEY is not set, so images cannot be read")

    monkeypatch.setattr(ingest, "extract_receipt", fail)

    response = writing_client.post("/api/evidence/receipt", files={"image": JPEG}, headers=DEVICE)

    assert response.status_code == 502
    assert "could not be read" in response.json()["detail"]


def test_a_pdf_upload_is_refused(writing_client: TestClient) -> None:
    response = writing_client.post(
        "/api/evidence/receipt",
        files={"image": ("receipt.pdf", b"%PDF-1.4", "application/pdf")},
        headers=DEVICE,
    )

    assert response.status_code == 415
    assert "image/jpeg" in response.json()["detail"]


def test_an_oversized_upload_is_refused(writing_client: TestClient) -> None:
    response = writing_client.post(
        "/api/evidence/receipt",
        files={"image": ("receipt.jpg", b"0" * (9 * 1024 * 1024), "image/jpeg")},
        headers=DEVICE,
    )

    assert response.status_code == 413
    assert "8MB" in response.json()["detail"]


def test_the_device_limit_answers_429_with_a_retry_after(
    writing_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rate_limit, "_by_device", rate_limit.SlidingWindow(rate_limit.Limit(2, 60)))

    files = {"image": JPEG}
    for _ in range(2):
        allowed = writing_client.post("/api/evidence/shelf", files=files, headers=DEVICE)
        assert allowed.status_code != 429
    blocked = writing_client.post("/api/evidence/shelf", files=files, headers=DEVICE)

    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    assert "Too many uploads from this device" in blocked.json()["detail"]


def test_a_different_device_is_not_punished_for_a_noisy_one(
    writing_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rate_limit, "_by_device", rate_limit.SlidingWindow(rate_limit.Limit(1, 60)))

    files = {"image": JPEG}
    writing_client.post("/api/evidence/shelf", files=files, headers={"X-Device-Id": "noisy"})
    blocked = writing_client.post(
        "/api/evidence/shelf", files=files, headers={"X-Device-Id": "noisy"}
    )
    other = writing_client.post(
        "/api/evidence/shelf", files=files, headers={"X-Device-Id": "quiet"}
    )

    assert blocked.status_code == 429
    assert other.status_code != 429


@pytest.mark.asyncio
async def test_alias_write_back_records_who_taught_it(
    writable_session: AsyncSession,
) -> None:
    match = await normalize.resolve_text(writable_session, "SHEGA SUGAR 1KG", source="receipt")
    await writable_session.flush()

    assert match.product is not None
    assert match.product.id == SUGAR.id
    assert match.method == "trigram"
    alias = await writable_session.scalar(
        select(ProductAlias).where(ProductAlias.normalized_text == "shega sugar 1kg")
    )
    assert alias.source == "receipt"
    assert alias.raw_text == "SHEGA SUGAR 1KG"


@pytest.fixture
def gemini_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pretend a Gemini key is configured, without making any calls."""
    monkeypatch.setattr(
        normalize,
        "get_settings",
        lambda: SimpleNamespace(gemini_api_key="test-key"),
    )


@pytest.mark.asyncio
async def test_gemini_settles_a_match_trigram_could_not(
    writable_session: AsyncSession,
    gemini_available: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[str] = []

    async def choose(raw_text: str, candidates: list[object]) -> CatalogChoice:
        asked.append(raw_text)
        assert candidates
        return CatalogChoice(match="existing", product_id=str(OIL.id), confidence=0.93)

    monkeypatch.setattr(normalize, "choose_catalog_match", choose)

    # Too far from any alias for trigram similarity to decide on its own.
    match = await normalize.resolve_text(writable_session, "Hayat Vegetable Oil 1 L")

    assert asked == ["Hayat Vegetable Oil 1 L"]
    assert match.method == "gemini"
    assert match.product is not None and match.product.id == OIL.id
    assert match.confidence == 0.93

    repeated = await normalize.resolve_text(writable_session, "Hayat Vegetable Oil 1 L")
    assert repeated.method == "alias_exact"
    assert len(asked) == 1


@pytest.mark.asyncio
async def test_a_gemini_outage_leaves_the_line_unmatched(
    writable_session: AsyncSession,
    gemini_available: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail(raw_text: str, candidates: list[object]) -> CatalogChoice:
        del raw_text, candidates
        raise ExtractionError("Gemini call failed")

    monkeypatch.setattr(normalize, "choose_catalog_match", fail)

    match = await normalize.resolve_text(writable_session, "Hayat Vegetable Oil 1 L")

    assert match.product is None
    assert match.method == "new_product"


@pytest.mark.asyncio
async def test_the_gate_still_rejects_an_absurd_price_from_a_receipt(
    writing_client: TestClient,
    writable_session: AsyncSession,
    gemini_receipt,
) -> None:
    gemini_receipt(receipt((OIL.canonical_name, 4200.0)))

    response = writing_client.post("/api/evidence/receipt", files={"image": JPEG}, headers=DEVICE)

    decision = response.json()["decisions"][0]
    assert decision["status"] == "rejected"
    assert "outside the" in decision["reason"]

    writable_session.expire_all()
    stored = await writable_session.get(Evidence, UUID(decision["id"]))
    assert stored.status is EvidenceStatus.REJECTED
    assert stored.rejection_reason == decision["reason"]
