"""Derive price estimates and confidence from accepted evidence.

Every number the API reports comes from here. The scoring half is pure
functions over weighted observations so it can be tested without a database;
the persistence half writes what those functions decided, including the
breakdown the product page renders instead of recomputing.
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from itertools import pairwise
from math import log
from typing import Literal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EvidenceSource, EvidenceStatus
from app.models.evidence import Evidence
from app.models.price import PriceEstimate, PriceHistory
from app.schemas.common import ConfidenceBand, ConfidenceBreakdown, ConfidenceFactor

Scope = Literal["market", "store"]

LOOKBACK_DAYS = 30
FRESHNESS_HALF_LIFE_DAYS = 7.0

SOURCE_WEIGHTS: dict[EvidenceSource, float] = {
    EvidenceSource.PARTNER: 1.0,
    EvidenceSource.RECEIPT: 0.9,
    EvidenceSource.SCRAPE: 0.75,
    EvidenceSource.STORE_VISIT: 0.6,
    EvidenceSource.SHELF_PHOTO: 0.55,
    EvidenceSource.COMMUNITY: 0.4,
}

FACTOR_WEIGHTS: dict[str, float] = {
    "volume": 0.30,
    "agreement": 0.30,
    "freshness": 0.25,
    "diversity": 0.15,
}

VOLUME_TARGET_WEIGHT = 8.0
AGREEMENT_TOLERANCE = 0.25
MARKET_STORE_TARGET = 3
STORE_EVIDENCE_TARGET = 2
STALE_FRESHNESS = 0.30
STALE_CONFIDENCE_CAP = 60
HIGH_BAND_MIN = 85
MEDIUM_BAND_MIN = 65

_MONEY = Decimal("0.01")
_SPREAD = Decimal("0.000001")


@dataclass(frozen=True, slots=True)
class Observation:
    """One evidence row as the engine sees it."""

    price_etb: float
    source_type: EvidenceSource
    observed_at: datetime
    ocr_confidence: float = 1.0
    store_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class WeightedObservation:
    price_etb: float
    weight: float
    freshness: float
    observed_at: datetime
    store_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class Estimate:
    price_etb: float
    confidence: int
    evidence_count: int
    store_count: int
    spread_pct: float
    newest_observed_at: datetime
    breakdown: ConfidenceBreakdown


def _clamp(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _money(value: float) -> Decimal:
    return Decimal(str(value)).quantize(_MONEY, rounding=ROUND_HALF_UP)


def freshness_weight(observed_at: datetime, now: datetime) -> float:
    """Halve the weight of an observation every seven days."""
    age_days = max((_as_utc(now) - _as_utc(observed_at)).total_seconds() / 86_400, 0.0)
    return 0.5 ** (age_days / FRESHNESS_HALF_LIFE_DAYS)


def weigh(observation: Observation, now: datetime) -> WeightedObservation:
    freshness = freshness_weight(observation.observed_at, now)
    source_weight = SOURCE_WEIGHTS[observation.source_type]
    return WeightedObservation(
        price_etb=observation.price_etb,
        weight=source_weight * _clamp(observation.ocr_confidence) * freshness,
        freshness=freshness,
        observed_at=_as_utc(observation.observed_at),
        store_id=observation.store_id,
    )


def weigh_all(
    observations: Iterable[Observation],
    now: datetime,
    *,
    lookback_days: int = LOOKBACK_DAYS,
) -> list[WeightedObservation]:
    cutoff = _as_utc(now) - timedelta(days=lookback_days)
    weighted = [
        weigh(observation, now)
        for observation in observations
        if _as_utc(observation.observed_at) > cutoff
    ]
    return [item for item in weighted if item.weight > 0]


def weighted_quantile(observations: Sequence[WeightedObservation], quantile: float) -> float:
    """Interpolate a quantile over weighted prices.

    Each observation covers the weight-proportional interval centred on its own
    midpoint, so equal weights reproduce the textbook median.
    """
    if not observations:
        raise ValueError("weighted_quantile needs at least one observation")

    ordered = sorted(observations, key=lambda item: item.price_etb)
    total_weight = sum(item.weight for item in ordered)
    if total_weight <= 0:
        raise ValueError("weighted_quantile needs a positive total weight")

    points: list[tuple[float, float]] = []
    cumulative = 0.0
    for item in ordered:
        cumulative += item.weight
        points.append(((cumulative - item.weight / 2) / total_weight, item.price_etb))

    if quantile <= points[0][0]:
        return points[0][1]
    if quantile >= points[-1][0]:
        return points[-1][1]

    for (left_at, left_price), (right_at, right_price) in pairwise(points):
        if quantile <= right_at:
            span = right_at - left_at
            share = 0.0 if span == 0 else (quantile - left_at) / span
            return left_price + share * (right_price - left_price)

    return points[-1][1]


def weighted_median(observations: Sequence[WeightedObservation]) -> float:
    return weighted_quantile(observations, 0.5)


def spread(observations: Sequence[WeightedObservation]) -> float:
    """Interquartile range as a fraction of the median."""
    median = weighted_median(observations)
    if median <= 0:
        return 0.0
    p25 = weighted_quantile(observations, 0.25)
    p75 = weighted_quantile(observations, 0.75)
    return max((p75 - p25) / median, 0.0)


def volume_score(observations: Sequence[WeightedObservation]) -> float:
    total_weight = sum(item.weight for item in observations)
    return _clamp(log(1 + total_weight) / log(1 + VOLUME_TARGET_WEIGHT))


def agreement_score(spread_pct: float) -> float:
    return _clamp(1 - spread_pct / AGREEMENT_TOLERANCE)


def freshness_score(observations: Sequence[WeightedObservation]) -> float:
    return _clamp(max(item.freshness for item in observations))


def diversity_score(observations: Sequence[WeightedObservation], scope: Scope) -> float:
    if scope == "market":
        return _clamp(distinct_stores(observations) / MARKET_STORE_TARGET)
    return _clamp(len(observations) / STORE_EVIDENCE_TARGET)


def distinct_stores(observations: Sequence[WeightedObservation]) -> int:
    return len({item.store_id for item in observations if item.store_id is not None})


def band_for(confidence: int) -> ConfidenceBand:
    if confidence >= HIGH_BAND_MIN:
        return "high"
    if confidence >= MEDIUM_BAND_MIN:
        return "medium"
    return "low"


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _humanize_age(observed_at: datetime, now: datetime) -> str:
    seconds = max((_as_utc(now) - _as_utc(observed_at)).total_seconds(), 0.0)
    if seconds < 3_600:
        return _plural(max(int(seconds // 60), 1), "minute")
    if seconds < 86_400:
        return _plural(int(seconds // 3_600), "hour")
    return _plural(int(seconds // 86_400), "day")


def estimate(
    observations: Sequence[WeightedObservation],
    *,
    scope: Scope = "market",
    now: datetime | None = None,
) -> Estimate | None:
    """Score one product, either market-wide or for a single store."""
    if not observations:
        return None

    moment = _as_utc(now) if now is not None else datetime.now(timezone.utc)
    newest_observed_at = max(item.observed_at for item in observations)
    store_count = distinct_stores(observations)

    spread_pct = spread(observations)
    scores = {
        "volume": volume_score(observations),
        "agreement": agreement_score(spread_pct),
        "freshness": freshness_score(observations),
        "diversity": diversity_score(observations, scope),
    }
    raw_confidence = 100 * sum(scores[name] * FACTOR_WEIGHTS[name] for name in FACTOR_WEIGHTS)

    confidence = round(raw_confidence)
    capped = scores["freshness"] < STALE_FRESHNESS and confidence > STALE_CONFIDENCE_CAP
    if capped:
        confidence = STALE_CONFIDENCE_CAP

    age = _humanize_age(newest_observed_at, moment)
    details = {
        "volume": _plural(len(observations), "accepted report"),
        "agreement": f"Prices agree within {spread_pct:.1%}",
        "freshness": f"Newest report was {age} ago",
        "diversity": (
            f"Verified across {_plural(store_count, 'store')}"
            if scope == "market"
            else f"{_plural(len(observations), 'report')} from this store"
        ),
    }
    breakdown = ConfidenceBreakdown(
        score=confidence,
        band=band_for(confidence),
        factors=[
            ConfidenceFactor(
                name=name,
                score=round(scores[name], 4),
                weight=FACTOR_WEIGHTS[name],
                detail=details[name],
            )
            for name in FACTOR_WEIGHTS
        ],
        capped=capped,
        cap_reason=(
            f"Newest report is {age} old, so confidence is capped at {STALE_CONFIDENCE_CAP}."
            if capped
            else None
        ),
    )

    return Estimate(
        price_etb=round(weighted_median(observations), 2),
        confidence=confidence,
        evidence_count=len(observations),
        store_count=store_count,
        spread_pct=round(spread_pct, 6),
        newest_observed_at=newest_observed_at,
        breakdown=breakdown,
    )


async def load_observations(
    session: AsyncSession,
    product_id: UUID,
    *,
    now: datetime,
    lookback_days: int = LOOKBACK_DAYS,
) -> list[WeightedObservation]:
    """Read the accepted evidence inside the lookback window and weigh it."""
    cutoff = _as_utc(now) - timedelta(days=lookback_days)
    rows = await session.scalars(
        select(Evidence).where(
            Evidence.product_id == product_id,
            Evidence.status == EvidenceStatus.ACCEPTED,
            Evidence.observed_at > cutoff,
        )
    )
    return weigh_all(
        (
            Observation(
                price_etb=float(row.price_etb),
                source_type=row.source_type,
                observed_at=row.observed_at,
                ocr_confidence=float(row.ocr_confidence),
                store_id=row.store_id,
            )
            for row in rows
        ),
        now,
        lookback_days=lookback_days,
    )


async def recompute_product(
    session: AsyncSession,
    product_id: UUID,
    *,
    now: datetime | None = None,
) -> Estimate | None:
    """Rebuild every estimate and history row for one product.

    Flushes but does not commit, so an ingest request can gate, insert, and
    recompute inside a single transaction.
    """
    moment = _as_utc(now) if now is not None else datetime.now(timezone.utc)
    observations = await load_observations(session, product_id, now=moment)

    market = estimate(observations, scope="market", now=moment)
    if market is None:
        await session.execute(delete(PriceEstimate).where(PriceEstimate.product_id == product_id))
        await session.flush()
        return None

    await _write_estimate(session, product_id, None, market, moment)

    store_ids = {item.store_id for item in observations if item.store_id is not None}
    for store_id in store_ids:
        subset = [item for item in observations if item.store_id == store_id]
        store_estimate = estimate(subset, scope="store", now=moment)
        if store_estimate is not None:
            await _write_estimate(session, product_id, store_id, store_estimate, moment)

    stale_estimates = delete(PriceEstimate).where(
        PriceEstimate.product_id == product_id,
        PriceEstimate.store_id.is_not(None),
    )
    if store_ids:
        stale_estimates = stale_estimates.where(PriceEstimate.store_id.not_in(store_ids))
    await session.execute(stale_estimates)
    await _write_history(session, product_id, observations)
    await session.flush()
    return market


async def _write_estimate(
    session: AsyncSession,
    product_id: UUID,
    store_id: UUID | None,
    result: Estimate,
    computed_at: datetime,
) -> None:
    scope_filter = (
        PriceEstimate.store_id.is_(None) if store_id is None else PriceEstimate.store_id == store_id
    )
    row = await session.scalar(
        select(PriceEstimate).where(PriceEstimate.product_id == product_id, scope_filter)
    )
    if row is None:
        row = PriceEstimate(product_id=product_id, store_id=store_id)
        session.add(row)

    row.price_etb = _money(result.price_etb)
    row.confidence = result.confidence
    row.evidence_count = result.evidence_count
    row.store_count = result.store_count
    row.spread_pct = Decimal(str(result.spread_pct)).quantize(_SPREAD, rounding=ROUND_HALF_UP)
    row.newest_observed_at = result.newest_observed_at
    row.breakdown = result.breakdown.model_dump()
    row.computed_at = computed_at


async def _write_history(
    session: AsyncSession,
    product_id: UUID,
    observations: Sequence[WeightedObservation],
) -> None:
    by_day: dict[date, list[WeightedObservation]] = defaultdict(list)
    for item in observations:
        by_day[item.observed_at.date()].append(item)

    existing = {
        row.day: row
        for row in await session.scalars(
            select(PriceHistory).where(
                PriceHistory.product_id == product_id,
                PriceHistory.day.in_(list(by_day)),
            )
        )
    }
    for day, group in by_day.items():
        row = existing.get(day)
        if row is None:
            row = PriceHistory(product_id=product_id, day=day)
            session.add(row)
        row.price_etb = _money(round(weighted_median(group), 2))
        row.evidence_count = len(group)
