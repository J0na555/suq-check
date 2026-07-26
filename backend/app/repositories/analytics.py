"""Price movement over a window, read straight out of `price_history`.

The dashboard's trends page and Market Pulse's movers are the same measurement
asked two different ways, so both read `price_changes`.

Unit economics reads token counts off `evidence.raw_payload["gemini"]` and
prices them with the constants in `app.costing`.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.costing import (
    COST_BENCHMARKS,
    GEMINI_INPUT_USD_PER_MTOK,
    GEMINI_OUTPUT_USD_PER_MTOK,
    USD_TO_ETB,
    allocated_tokens,
    gemini_cost_usd,
    usd_to_etb,
)
from app.models.enums import EvidenceStatus, ProductCategory
from app.models.evidence import Evidence
from app.models.price import PriceHistory
from app.models.product import Product
from app.schemas.analytics import (
    CostBenchmark,
    ProductTrend,
    SourceEconomics,
    TrendPoint,
    TrendsResponse,
    UnitEconomicsResponse,
)

# Anything inside a percent either way is noise, not a trend.
STABLE_BAND_PCT = 1.0
TREND_LIMIT = 12

Direction = Literal["up", "down", "stable"]


@dataclass
class _SourceBucket:
    observations: int = 0
    verified_observations: int = 0
    prompt_tokens: float = 0.0
    candidates_tokens: float = 0.0
    total_tokens: float = 0.0

    def add(self, *, verified: bool, gemini: dict[str, Any] | None) -> None:
        self.observations += 1
        if verified:
            self.verified_observations += 1
        if not gemini:
            return
        share = gemini.get("shared_across_observations")
        self.prompt_tokens += allocated_tokens(gemini.get("prompt_token_count"), shared_across=share)
        self.candidates_tokens += allocated_tokens(
            gemini.get("candidates_token_count"),
            shared_across=share,
        )
        self.total_tokens += allocated_tokens(gemini.get("total_token_count"), shared_across=share)


@dataclass(frozen=True, slots=True)
class PriceChange:
    product_id: UUID
    product_name: str
    change_pct: float
    points: list[TrendPoint]

    @property
    def direction(self) -> Direction:
        if self.change_pct > STABLE_BAND_PCT:
            return "up"
        if self.change_pct < -STABLE_BAND_PCT:
            return "down"
        return "stable"


async def price_changes(
    session: AsyncSession,
    *,
    period_days: int,
    now: datetime | None = None,
    category: str | None = None,
) -> list[PriceChange]:
    """One entry per product with at least two priced days in the window."""
    moment = now or datetime.now(timezone.utc)
    filters = [PriceHistory.day >= (moment - timedelta(days=period_days)).date()]
    if category:
        filters.append(Product.category == ProductCategory(category))
    rows = await session.execute(
        select(Product.id, Product.canonical_name, PriceHistory.day, PriceHistory.price_etb)
        .join(PriceHistory, PriceHistory.product_id == Product.id)
        .where(*filters)
        .order_by(Product.canonical_name, PriceHistory.day)
    )

    series: dict[UUID, tuple[str, list[TrendPoint]]] = {}
    for product_id, name, day, price_etb in rows:
        _, points = series.setdefault(product_id, (name, []))
        points.append(TrendPoint(day=day, price_etb=float(price_etb)))

    changes = []
    for product_id, (name, points) in series.items():
        if len(points) < 2 or points[0].price_etb <= 0:
            continue
        change_pct = 100 * (points[-1].price_etb - points[0].price_etb) / points[0].price_etb
        changes.append(
            PriceChange(
                product_id=product_id,
                product_name=name,
                change_pct=round(change_pct, 1),
                points=points,
            )
        )
    return changes


async def load_trends(
    session: AsyncSession,
    *,
    period_days: int,
    now: datetime | None = None,
    category: str | None = None,
    limit: int = TREND_LIMIT,
) -> TrendsResponse:
    changes = await price_changes(
        session,
        period_days=period_days,
        now=now,
        category=category,
    )
    moved_most = sorted(changes, key=lambda change: abs(change.change_pct), reverse=True)
    return TrendsResponse(
        period_days=period_days,
        items=[
            ProductTrend(
                product_id=change.product_id,
                product_name=change.product_name,
                direction=change.direction,
                change_pct=change.change_pct,
                points=change.points,
            )
            for change in moved_most[:limit]
        ],
    )


async def load_unit_economics(
    session: AsyncSession,
    *,
    period_days: int,
    now: datetime | None = None,
) -> UnitEconomicsResponse:
    """Observations, Gemini tokens, and ETB spend for a trailing window."""
    moment = now or datetime.now(timezone.utc)
    rows = await session.execute(
        select(Evidence.source_type, Evidence.status, Evidence.raw_payload).where(
            Evidence.observed_at >= moment - timedelta(days=period_days)
        )
    )

    by_source: dict[str, _SourceBucket] = {}
    totals = _SourceBucket()
    for source_type, status, raw_payload in rows:
        source = source_type.value if hasattr(source_type, "value") else str(source_type)
        payload = raw_payload or {}
        gemini = payload.get("gemini") if isinstance(payload.get("gemini"), dict) else None
        verified = status is EvidenceStatus.ACCEPTED or status == EvidenceStatus.ACCEPTED.value
        bucket = by_source.setdefault(source, _SourceBucket())
        bucket.add(verified=verified, gemini=gemini)
        totals.add(verified=verified, gemini=gemini)

    cost_usd = gemini_cost_usd(
        prompt_tokens=totals.prompt_tokens,
        candidates_tokens=totals.candidates_tokens,
    )
    cost_etb = usd_to_etb(cost_usd)

    return UnitEconomicsResponse(
        period_days=period_days,
        observations=totals.observations,
        verified_observations=totals.verified_observations,
        prompt_tokens=round(totals.prompt_tokens, 2),
        candidates_tokens=round(totals.candidates_tokens, 2),
        total_tokens=round(totals.total_tokens, 2),
        gemini_cost_usd=round(cost_usd, 6),
        gemini_cost_etb=round(cost_etb, 4),
        cost_per_verified_observation_etb=_per_verified(cost_etb, totals.verified_observations),
        usd_to_etb=USD_TO_ETB,
        gemini_input_usd_per_mtok=GEMINI_INPUT_USD_PER_MTOK,
        gemini_output_usd_per_mtok=GEMINI_OUTPUT_USD_PER_MTOK,
        by_source=[
            _source_economics(source, bucket) for source, bucket in sorted(by_source.items())
        ],
        benchmarks=[
            CostBenchmark(
                id=item.id,
                label=item.label,
                min_etb=item.min_etb,
                max_etb=item.max_etb,
                unit=item.unit,
                source=item.source,
            )
            for item in COST_BENCHMARKS
        ],
    )


def _source_economics(source: str, bucket: _SourceBucket) -> SourceEconomics:
    cost_etb = usd_to_etb(
        gemini_cost_usd(
            prompt_tokens=bucket.prompt_tokens,
            candidates_tokens=bucket.candidates_tokens,
        )
    )
    return SourceEconomics(
        source_type=source,
        observations=bucket.observations,
        verified_observations=bucket.verified_observations,
        prompt_tokens=round(bucket.prompt_tokens, 2),
        candidates_tokens=round(bucket.candidates_tokens, 2),
        total_tokens=round(bucket.total_tokens, 2),
        gemini_cost_etb=round(cost_etb, 4),
        cost_per_verified_observation_etb=_per_verified(cost_etb, bucket.verified_observations),
    )


def _per_verified(cost_etb: float, verified: int) -> float | None:
    if verified <= 0:
        return None
    return round(cost_etb / verified, 4)
