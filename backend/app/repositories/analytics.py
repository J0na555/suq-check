"""Price movement over a window, read straight out of `price_history`.

The dashboard's trends page and Market Pulse's movers are the same measurement
asked two different ways, so both read `price_changes`.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price import PriceHistory
from app.models.product import Product
from app.schemas.analytics import ProductTrend, TrendPoint, TrendsResponse

# Anything inside a percent either way is noise, not a trend.
STABLE_BAND_PCT = 1.0
TREND_LIMIT = 12

Direction = Literal["up", "down", "stable"]


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
) -> list[PriceChange]:
    """One entry per product with at least two priced days in the window."""
    moment = now or datetime.now(timezone.utc)
    rows = await session.execute(
        select(Product.id, Product.canonical_name, PriceHistory.day, PriceHistory.price_etb)
        .join(PriceHistory, PriceHistory.product_id == Product.id)
        .where(PriceHistory.day >= (moment - timedelta(days=period_days)).date())
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
    limit: int = TREND_LIMIT,
) -> TrendsResponse:
    changes = await price_changes(session, period_days=period_days, now=now)
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
