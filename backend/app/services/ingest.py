"""The write path: an image or a form becomes gated, weighted evidence.

Each function reads what was submitted, matches it to the catalog, puts the
price through the verification gate, and returns the decision the shopper is
shown. Nothing here sets a price or a confidence score; `submit_evidence` writes
the evidence row and asks the engine to recompute.

Unmatched receipt lines are reported back but never written. Inventing a product
from a line of OCR would put unverifiable rows in the catalog, and the app
already shows the extraction for correction before anything is submitted.
"""

from datetime import date, datetime, time, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.uploads import Image
from app.models.enums import EvidenceSource, ProductCategory, SizeUnit
from app.models.evidence import Evidence
from app.models.product import Product
from app.models.store import Store
from app.repositories.stores import find_store_by_name
from app.schemas.evidence import (
    EvidenceDecision,
    ExtractedLineItem,
    ManualEvidenceRequest,
    ManualEvidenceResponse,
    OosEvidenceRequest,
    OosEvidenceResponse,
    PriceListExtraction,
    PriceListUploadResponse,
    ProductIdentification,
    ReceiptExtraction,
    ReceiptUploadResponse,
    ShelfExtraction,
    ShelfUploadResponse,
)
from app.services import thumbnail
from app.services.normalize import Match, resolve_text
from app.services.ocr import (
    ExtractionError,
    GeminiUsage,
    PriceListLine,
    ReceiptLine,
    extract_price_list,
    extract_receipt,
    extract_shelf_tag,
    identify_product,
    pop_usage,
)
from app.services.verification import Decision, submit_evidence, submit_oos_evidence


class MissingReference(LookupError):
    """A submission pointed at a product or store that does not exist."""


async def ingest_receipt(
    session: AsyncSession,
    image: Image,
    *,
    device_id: str | None = None,
    now: datetime | None = None,
) -> ReceiptUploadResponse:
    moment = now or datetime.now(timezone.utc)
    receipt = await extract_receipt(image.data, image.mime_type)
    # Pop before resolve_text: catalog matching may call Gemini and overwrite usage.
    usage = pop_usage()
    store = await find_store_by_name(session, receipt.store_name)
    observed_at = _printed_moment(receipt.observed_date, moment)
    small_copy = thumbnail.of(image.data)

    items: list[ExtractedLineItem] = []
    decisions: list[EvidenceDecision] = []
    matched_lines: list[tuple[ReceiptLine, Match]] = []
    for line in receipt.items:
        match = await resolve_text(session, line.raw_text, source="receipt")
        items.append(
            ExtractedLineItem(
                raw_text=line.raw_text,
                quantity=line.quantity,
                unit_price_etb=line.unit_price_etb,
                total_price_etb=line.total_price_etb,
                matched_product_id=match.product.id if match.product else None,
                matched_product_name=match.product.canonical_name if match.product else None,
                match_confidence=round(match.confidence, 4),
            )
        )
        if match.product is None:
            continue
        matched_lines.append((line, match))

    shared = len(matched_lines)
    for line, match in matched_lines:
        product = match.product
        assert product is not None
        evidence, decision = await submit_evidence(
            session,
            product=product,
            price_etb=line.unit_price_etb,
            source_type=EvidenceSource.RECEIPT,
            observed_at=observed_at,
            store_id=store.id if store else None,
            ocr_confidence=receipt.ocr_confidence,
            raw_payload=_payload(
                device_id,
                raw_text=line.raw_text,
                match_method=match.method,
                store_name=receipt.store_name,
                gemini=_gemini_payload(usage, shared_across=shared),
            ),
            thumbnail=small_copy,
            now=moment,
        )
        decisions.append(_decision(evidence, product, decision))

    return ReceiptUploadResponse(
        extraction=ReceiptExtraction(
            store_name=store.name if store else receipt.store_name,
            observed_on=receipt.observed_date,
            total_etb=receipt.total_etb,
            ocr_confidence=receipt.ocr_confidence,
            items=items,
        ),
        decisions=decisions,
    )


async def ingest_price_list(
    session: AsyncSession,
    image: Image,
    *,
    store_id: UUID,
    device_id: str | None = None,
    now: datetime | None = None,
) -> PriceListUploadResponse:
    """Posted price list under Directive 159/2024: many lines, known store."""
    moment = now or datetime.now(timezone.utc)
    store = await session.get(Store, store_id)
    if store is None:
        raise MissingReference("Store not found")

    document = await extract_price_list(image.data, image.mime_type)
    usage = pop_usage()
    observed_at = _printed_moment(document.observed_date, moment)
    small_copy = thumbnail.of(image.data)

    items: list[ExtractedLineItem] = []
    decisions: list[EvidenceDecision] = []
    matched_lines: list[tuple[PriceListLine, Match]] = []
    for line in document.items:
        match = await resolve_text(session, line.raw_text, source="price_list")
        items.append(
            ExtractedLineItem(
                raw_text=line.raw_text,
                quantity=1,
                unit_price_etb=line.price_etb,
                total_price_etb=line.price_etb,
                matched_product_id=match.product.id if match.product else None,
                matched_product_name=match.product.canonical_name if match.product else None,
                match_confidence=round(match.confidence, 4),
            )
        )
        if match.product is None:
            continue
        matched_lines.append((line, match))

    shared = len(matched_lines)
    for line, match in matched_lines:
        product = match.product
        assert product is not None
        evidence, decision = await submit_evidence(
            session,
            product=product,
            price_etb=line.price_etb,
            source_type=EvidenceSource.STORE_VISIT,
            observed_at=observed_at,
            store_id=store.id,
            ocr_confidence=document.ocr_confidence,
            raw_payload=_payload(
                device_id,
                raw_text=line.raw_text,
                match_method=match.method,
                store_name=store.name,
                gemini=_gemini_payload(usage, shared_across=shared),
            ),
            thumbnail=small_copy,
            now=moment,
        )
        decisions.append(_decision(evidence, product, decision))

    return PriceListUploadResponse(
        extraction=PriceListExtraction(
            store_id=store.id,
            store_name=store.name,
            observed_on=document.observed_date,
            ocr_confidence=document.ocr_confidence,
            items=items,
        ),
        decisions=decisions,
    )


async def ingest_shelf_tag(
    session: AsyncSession,
    image: Image,
    *,
    device_id: str | None = None,
    now: datetime | None = None,
) -> ShelfUploadResponse:
    moment = now or datetime.now(timezone.utc)
    tag = await extract_shelf_tag(image.data, image.mime_type)
    usage = pop_usage()
    match = await resolve_text(session, tag.raw_product_text, source="shelf_photo")
    if match.product is None:
        raise MissingReference(
            f"{tag.raw_product_text!r} is not in the catalog yet, so its price cannot be recorded."
        )

    evidence, decision = await submit_evidence(
        session,
        product=match.product,
        price_etb=tag.price_etb,
        source_type=EvidenceSource.SHELF_PHOTO,
        observed_at=moment,
        ocr_confidence=tag.ocr_confidence,
        raw_payload=_payload(
            device_id,
            raw_text=tag.raw_product_text,
            match_method=match.method,
            gemini=_gemini_payload(usage, shared_across=1),
        ),
        thumbnail=thumbnail.of(image.data),
        now=moment,
    )

    return ShelfUploadResponse(
        extraction=ShelfExtraction(
            raw_product_text=tag.raw_product_text,
            price_etb=tag.price_etb,
            matched_product_id=match.product.id,
            matched_product_name=match.product.canonical_name,
            ocr_confidence=tag.ocr_confidence,
            match_confidence=round(match.confidence, 4),
        ),
        decision=_decision(evidence, match.product, decision),
    )


async def ingest_manual_report(
    session: AsyncSession,
    request: ManualEvidenceRequest,
    *,
    device_id: str | None = None,
    now: datetime | None = None,
) -> ManualEvidenceResponse:
    moment = now or datetime.now(timezone.utc)
    product = await session.get(Product, request.product_id)
    if product is None:
        raise MissingReference("Product not found")
    store = await session.get(Store, request.store_id)
    if store is None:
        raise MissingReference("Store not found")

    evidence, decision = await submit_evidence(
        session,
        product=product,
        price_etb=request.price_etb,
        source_type=EvidenceSource(request.source_type),
        # A phone with a wrong clock must not make a report look fresher than it
        # is, so a future timestamp is pulled back to now.
        observed_at=min(request.observed_at, moment),
        store_id=store.id,
        raw_payload=_payload(device_id, store_name=store.name),
        now=moment,
    )
    return ManualEvidenceResponse(decision=_decision(evidence, product, decision))


async def ingest_oos_report(
    session: AsyncSession,
    request: OosEvidenceRequest,
    *,
    device_id: str | None = None,
    now: datetime | None = None,
) -> OosEvidenceResponse:
    moment = now or datetime.now(timezone.utc)
    product = await session.get(Product, request.product_id)
    if product is None:
        raise MissingReference("Product not found")
    store = await session.get(Store, request.store_id)
    if store is None:
        raise MissingReference("Store not found")

    evidence, decision = await submit_oos_evidence(
        session,
        product=product,
        store_id=store.id,
        source_type=EvidenceSource(request.source_type),
        observed_at=min(request.observed_at, moment),
        raw_payload=_payload(device_id, store_name=store.name),
        now=moment,
    )
    return OosEvidenceResponse(decision=_decision(evidence, product, decision))


async def identify_from_image(session: AsyncSession, image: Image) -> ProductIdentification:
    seen = await identify_product(image.data, image.mime_type)
    match = await resolve_text(session, seen.canonical_name, source="scan", allow_gemini=False)

    if match.product is not None:
        product = match.product
        return ProductIdentification(
            product_id=product.id,
            canonical_name=product.canonical_name,
            brand=product.brand,
            category=product.category.value,
            size_value=float(product.size_value),
            size_unit=product.size_unit.value,
            confidence=round(min(seen.confidence, match.confidence), 4),
            match_method=match.method,
        )

    return ProductIdentification(
        product_id=None,
        canonical_name=seen.canonical_name,
        brand=seen.brand,
        category=_category(seen.category).value,
        size_unit=_size_unit(seen.size_unit).value,
        size_value=seen.size_value,
        confidence=round(seen.confidence, 4),
        match_method="gemini_vision",
    )


def _decision(evidence: Evidence, product: Product, decision: Decision) -> EvidenceDecision:
    return EvidenceDecision(
        id=evidence.id,
        product_id=product.id,
        product_name=product.canonical_name,
        price_etb=None if evidence.price_etb is None else float(evidence.price_etb),
        is_oos=evidence.is_oos,
        source_type=evidence.source_type.value,
        status=decision.status.value,
        reason=decision.reason,
    )


def _payload(device_id: str | None, **extra: Any) -> dict[str, Any]:
    return {"device_id": device_id, **{key: value for key, value in extra.items() if value}}


def _gemini_payload(usage: GeminiUsage | None, *, shared_across: int) -> dict[str, Any] | None:
    if usage is None:
        return None
    return usage.as_payload(shared_across_observations=max(shared_across, 1))


def _printed_moment(printed_on: date | None, now: datetime) -> datetime:
    """Trust the date on the receipt, but never a date in the future."""
    if printed_on is None:
        return now
    printed = datetime.combine(printed_on, time(12, 0), tzinfo=timezone.utc)
    return min(printed, now)


def _category(value: str) -> ProductCategory:
    try:
        return ProductCategory(value.strip().casefold())
    except ValueError as error:
        raise ExtractionError(f"{value!r} is not a supported category") from error


def _size_unit(value: str) -> SizeUnit:
    try:
        return SizeUnit(value.strip().casefold())
    except ValueError as error:
        raise ExtractionError(f"{value!r} is not a supported pack unit") from error
