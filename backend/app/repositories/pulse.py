"""The market at a glance, cached for a minute.

Pulse is the home screen, so it is the one endpoint every app launch hits. The
figures move slowly compared with how often they are asked for, which is what
the cache is for.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import monotonic
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EvidenceSource, EvidenceStatus
from app.models.evidence import Evidence
from app.models.price import PriceEstimate
from app.models.product import Product
from app.models.store import Store
from app.repositories.analytics import PriceChange, price_changes
from app.repositories.stores import PRICE_RATIO, store_prices_against_market
from app.schemas.pulse import PulseMetrics, PulseMover, PulseResponse

CACHE_SECONDS = 60
MOVER_PERIOD_DAYS = 7
REPORTING_WINDOW_DAYS = 30
# Rolling window so a seed (or field day) that landed yesterday evening still
# shows on the home screen after UTC midnight rolls over.
RECENT_ACTIVITY_HOURS = 24
UNKNOWN = "Not enough reports yet"

MoverKind = Literal["fastest_rising", "largest_drop", "most_stable", "most_verified"]

_MARKET_ESTIMATE = PriceEstimate.store_id.is_(None)


@dataclass(slots=True)
class _CachedPulse:
    expires_at: float
    response: PulseResponse


_cache: _CachedPulse | None = None


def clear_cache() -> None:
    global _cache
    _cache = None


async def load_pulse(session: AsyncSession, *, now: datetime | None = None) -> PulseResponse:
    global _cache
    if _cache is not None and _cache.expires_at > monotonic():
        return _cache.response

    response = await _build_pulse(session, now=now or datetime.now(timezone.utc))
    _cache = _CachedPulse(expires_at=monotonic() + CACHE_SECONDS, response=response)
    return response


async def _build_pulse(session: AsyncSession, *, now: datetime) -> PulseResponse:
    return PulseResponse(
        metrics=await _metrics(session, now=now),
        movers=await _movers(session, now=now),
        cheapest_district=await _cheapest_district(session),
        most_active_store=await _most_active_store(session, now=now),
    )


async def _metrics(session: AsyncSession, *, now: datetime) -> PulseMetrics:
    since = now - timedelta(hours=RECENT_ACTIVITY_HOURS)

    verified_today = await session.scalar(
        select(func.count())
        .select_from(Evidence)
        .where(
            Evidence.status == EvidenceStatus.ACCEPTED,
            Evidence.observed_at >= since,
        )
    )
    new_receipts_today = await session.scalar(
        select(func.count())
        .select_from(Evidence)
        .where(
            Evidence.source_type == EvidenceSource.RECEIPT,
            Evidence.created_at >= since,
        )
    )
    products_covered = await session.scalar(
        select(func.count()).select_from(PriceEstimate).where(_MARKET_ESTIMATE)
    )
    stores_reporting = await session.scalar(
        select(func.count(func.distinct(Evidence.store_id))).where(
            Evidence.status == EvidenceStatus.ACCEPTED,
            Evidence.observed_at >= now - timedelta(days=REPORTING_WINDOW_DAYS),
        )
    )
    average_confidence = await session.scalar(
        select(func.avg(PriceEstimate.confidence)).where(_MARKET_ESTIMATE)
    )

    return PulseMetrics(
        verified_prices_today=verified_today or 0,
        products_covered=products_covered or 0,
        stores_reporting=stores_reporting or 0,
        new_receipts_today=new_receipts_today or 0,
        average_confidence=round(float(average_confidence or 0)),
    )


async def _movers(session: AsyncSession, *, now: datetime) -> list[PulseMover]:
    changes = await price_changes(session, period_days=MOVER_PERIOD_DAYS, now=now)
    movers: list[PulseMover] = []

    if changes:
        rising = max(changes, key=lambda change: change.change_pct)
        dropping = min(changes, key=lambda change: change.change_pct)
        steadiest = min(changes, key=lambda change: abs(change.change_pct))
        if rising.change_pct > 0:
            movers.append(_percent_mover(rising, "fastest_rising"))
        if dropping.change_pct < 0:
            movers.append(_percent_mover(dropping, "largest_drop"))
        movers.append(_percent_mover(steadiest, "most_stable"))

    best = (
        await session.execute(
            select(Product.id, Product.canonical_name, PriceEstimate.confidence)
            .join(PriceEstimate, PriceEstimate.product_id == Product.id)
            .where(_MARKET_ESTIMATE)
            .order_by(PriceEstimate.confidence.desc(), PriceEstimate.evidence_count.desc())
            .limit(1)
        )
    ).first()
    if best is not None:
        product_id, name, confidence = best
        movers.append(
            PulseMover(
                product_id=product_id,
                product_name=name,
                kind="most_verified",
                value=confidence,
                display_value=f"{confidence}% confidence",
            )
        )
    return movers


def _percent_mover(change: PriceChange, kind: MoverKind) -> PulseMover:
    return PulseMover(
        product_id=change.product_id,
        product_name=change.product_name,
        kind=kind,
        value=change.change_pct,
        display_value=f"{change.change_pct:+.1f}%",
    )


async def _cheapest_district(session: AsyncSession) -> str:
    row = (
        await session.execute(
            store_prices_against_market(
                Store.district, func.avg(PRICE_RATIO).label("price_index")
            )
            .group_by(Store.district)
            .order_by("price_index")
            .limit(1)
        )
    ).first()
    return UNKNOWN if row is None else row.district


async def _most_active_store(session: AsyncSession, *, now: datetime) -> str:
    row = (
        await session.execute(
            select(Store.name, func.count().label("reports"))
            .join(Evidence, Evidence.store_id == Store.id)
            .where(
                Evidence.status == EvidenceStatus.ACCEPTED,
                Evidence.observed_at >= now - timedelta(days=MOVER_PERIOD_DAYS),
            )
            .group_by(Store.name)
            .order_by(func.count().desc())
            .limit(1)
        )
    ).first()
    return UNKNOWN if row is None else row.name
