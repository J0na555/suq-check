"""Decide whether an incoming price becomes evidence the engine trusts.

Two cheap checks in order: category bounds catch absurd numbers, then
deviation from the existing market estimate decides accepted, pending, or
rejected. Every branch produces a sentence a shopper can read, because the
dashboard's ingestion log and the contribute screen both show it.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category_bounds import CategoryPriceBounds
from app.models.enums import EvidenceSource, EvidenceStatus, ProductCategory, SizeUnit
from app.models.evidence import Evidence
from app.models.price import PriceEstimate
from app.models.product import Product
from app.services.price_engine import recompute_product

MIN_TRUSTED_CONFIDENCE = 60
PENDING_DEVIATION = 0.35
REJECT_DEVIATION = 1.50

UNIT_LABELS: dict[SizeUnit, str] = {
    SizeUnit.MILLILITER: "millilitre",
    SizeUnit.LITER: "litre",
    SizeUnit.GRAM: "gram",
    SizeUnit.KILOGRAM: "kilogram",
    SizeUnit.PIECE: "piece",
}


@dataclass(frozen=True, slots=True)
class PriceBounds:
    min_etb: float
    max_etb: float


@dataclass(frozen=True, slots=True)
class EstimateSnapshot:
    price_etb: float
    confidence: int


@dataclass(frozen=True, slots=True)
class Decision:
    status: EvidenceStatus
    reason: str


def _amount(value: float) -> str:
    """Render an ETB amount the way a price tag would."""
    return f"{value:.0f}" if float(value).is_integer() else f"{value:.2f}"


def _category_label(category: ProductCategory) -> str:
    return category.value.replace("_", " ")


def decide(
    price_etb: float,
    *,
    category: ProductCategory,
    size_unit: SizeUnit,
    bounds: PriceBounds | None = None,
    estimate: EstimateSnapshot | None = None,
) -> Decision:
    """Gate one price against category bounds and the current market estimate."""
    if bounds is not None and not bounds.min_etb <= price_etb <= bounds.max_etb:
        return Decision(
            status=EvidenceStatus.REJECTED,
            reason=(
                f"{_amount(price_etb)} ETB is outside the "
                f"{_amount(bounds.min_etb)}-{_amount(bounds.max_etb)} ETB range recorded for "
                f"{_category_label(category)} sold by the {UNIT_LABELS[size_unit]}."
            ),
        )

    if estimate is None or estimate.confidence < MIN_TRUSTED_CONFIDENCE or estimate.price_etb <= 0:
        return Decision(
            status=EvidenceStatus.ACCEPTED,
            reason="No verified estimate exists yet, so this report bootstraps the price.",
        )

    deviation = abs(price_etb - estimate.price_etb) / estimate.price_etb
    direction = "above" if price_etb > estimate.price_etb else "below"
    reference = f"{_amount(estimate.price_etb)} ETB market estimate"

    if deviation < PENDING_DEVIATION:
        return Decision(
            status=EvidenceStatus.ACCEPTED,
            reason=f"Price agrees with the {reference} within {deviation:.1%}.",
        )
    if deviation <= REJECT_DEVIATION:
        return Decision(
            status=EvidenceStatus.PENDING,
            reason=(
                f"Price is {deviation:.1%} {direction} the {reference} and needs verification."
            ),
        )
    return Decision(
        status=EvidenceStatus.REJECTED,
        reason=(
            f"Price is {deviation:.1%} {direction} the {reference}, "
            "far beyond what verification can explain."
        ),
    )


async def load_bounds(
    session: AsyncSession,
    category: ProductCategory,
    size_unit: SizeUnit,
) -> PriceBounds | None:
    row = await session.scalar(
        select(CategoryPriceBounds).where(
            CategoryPriceBounds.category == category,
            CategoryPriceBounds.size_unit == size_unit,
        )
    )
    if row is None:
        return None
    return PriceBounds(min_etb=float(row.min_etb), max_etb=float(row.max_etb))


async def load_market_estimate(session: AsyncSession, product_id: UUID) -> EstimateSnapshot | None:
    row = await session.scalar(
        select(PriceEstimate).where(
            PriceEstimate.product_id == product_id,
            PriceEstimate.store_id.is_(None),
        )
    )
    if row is None:
        return None
    return EstimateSnapshot(price_etb=float(row.price_etb), confidence=row.confidence)


async def gate_price(session: AsyncSession, product: Product, price_etb: float) -> Decision:
    return decide(
        price_etb,
        category=product.category,
        size_unit=product.size_unit,
        bounds=await load_bounds(session, product.category, product.size_unit),
        estimate=await load_market_estimate(session, product.id),
    )


async def submit_evidence(
    session: AsyncSession,
    *,
    product: Product,
    price_etb: float,
    source_type: EvidenceSource,
    observed_at: datetime,
    store_id: UUID | None = None,
    ocr_confidence: float = 1.0,
    raw_payload: dict[str, Any] | None = None,
    thumbnail: bytes | None = None,
    now: datetime | None = None,
) -> tuple[Evidence, Decision]:
    """Gate a price, store it as evidence, and recompute if it was accepted.

    Flushes but does not commit; the caller owns the transaction.
    """
    decision = await gate_price(session, product, price_etb)
    evidence = Evidence(
        product_id=product.id,
        store_id=store_id,
        price_etb=Decimal(str(price_etb)),
        is_oos=False,
        source_type=source_type,
        ocr_confidence=Decimal(str(ocr_confidence)),
        observed_at=observed_at,
        status=decision.status,
        rejection_reason=(
            None if decision.status == EvidenceStatus.ACCEPTED else decision.reason
        ),
        raw_payload=raw_payload or {},
        thumbnail=thumbnail,
    )
    session.add(evidence)
    await session.flush()

    if decision.status == EvidenceStatus.ACCEPTED:
        await recompute_product(
            session,
            product.id,
            now=now if now is not None else datetime.now(timezone.utc),
        )

    return evidence, decision


async def submit_oos_evidence(
    session: AsyncSession,
    *,
    product: Product,
    store_id: UUID,
    source_type: EvidenceSource,
    observed_at: datetime,
    ocr_confidence: float = 1.0,
    raw_payload: dict[str, Any] | None = None,
    thumbnail: bytes | None = None,
    now: datetime | None = None,
) -> tuple[Evidence, Decision]:
    """Record a verified out-of-stock observation and clear that store's estimate."""
    decision = Decision(
        status=EvidenceStatus.ACCEPTED,
        reason="Out-of-stock flag accepted; no price to gate.",
    )
    evidence = Evidence(
        product_id=product.id,
        store_id=store_id,
        price_etb=None,
        is_oos=True,
        source_type=source_type,
        ocr_confidence=Decimal(str(ocr_confidence)),
        observed_at=observed_at,
        status=decision.status,
        rejection_reason=None,
        raw_payload={**(raw_payload or {}), "is_oos": True},
        thumbnail=thumbnail,
    )
    session.add(evidence)
    await session.flush()

    await recompute_product(
        session,
        product.id,
        now=now if now is not None else datetime.now(timezone.utc),
    )
    return evidence, decision
