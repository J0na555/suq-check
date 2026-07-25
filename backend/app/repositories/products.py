"""Read products, their detail page, and their per-store prices.

Nothing here derives a price. The market and per-store numbers were written by
`services/price_engine.py`; these queries join them to the catalog and dress
them in contract shapes. The one exception is the quartile pair behind
`price_range_etb`, which the engine does not persist and which is cheap to
recompute for a single product.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ColumnElement, Select, and_, func, null, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EvidenceStatus, ProductCategory
from app.models.evidence import Evidence
from app.models.price import PriceEstimate, PriceHistory
from app.models.product import Product
from app.models.store import Store
from app.repositories.mappers import (
    as_utc,
    distance_expression,
    product_summary,
    source_label,
    verdict_for,
)
from app.schemas.common import ConfidenceBreakdown, HistoryPoint, SourceSummary
from app.schemas.products import (
    NearbyStorePrice,
    NearbyStoresResponse,
    ProductDetail,
    ProductListResponse,
)
from app.services.normalize import canonicalize, trigram_similarity
from app.services.price_engine import LOOKBACK_DAYS, load_observations, weighted_quantile

HISTORY_DAYS = 60
FUZZY_THRESHOLD = 0.30
FUZZY_CANDIDATES = 50

_MARKET_ESTIMATE = and_(
    PriceEstimate.product_id == Product.id,
    PriceEstimate.store_id.is_(None),
)


def _is_postgres(session: AsyncSession) -> bool:
    return session.get_bind().dialect.name == "postgresql"


def _listed_products() -> Select[tuple[Product, PriceEstimate]]:
    """Only products the engine has priced can be listed; the rest have no number."""
    return select(Product, PriceEstimate).join(PriceEstimate, _MARKET_ESTIMATE)


async def search_products(
    session: AsyncSession,
    *,
    query: str | None = None,
    category: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> ProductListResponse:
    filters: list[ColumnElement[bool]] = []
    if category:
        filters.append(Product.category == ProductCategory(category))
    if query:
        pattern = f"%{query.strip()}%"
        filters.append(or_(Product.canonical_name.ilike(pattern), Product.brand.ilike(pattern)))

    statement = _listed_products().where(*filters)
    total = await session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = (
        await session.execute(
            statement.order_by(PriceEstimate.confidence.desc(), Product.canonical_name)
            .limit(limit)
            .offset(offset)
        )
    ).all()

    if query and not rows and offset == 0:
        category_only = filters[:1] if category else []
        rows = await _fuzzy_search(session, query, category_only, limit)
        total = len(rows)

    return ProductListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[
            product_summary(product, estimate.price_etb, estimate.confidence)
            for product, estimate in rows
        ],
    )


async def _fuzzy_search(
    session: AsyncSession,
    query: str,
    conditions: list[ColumnElement[bool]],
    limit: int,
) -> list[tuple[Product, PriceEstimate]]:
    """Catch misspellings that `ILIKE` cannot, the way the normalizer does.

    Postgres scores with `pg_trgm`; anywhere else the same trigram measure runs
    in Python over the catalog, which is a few hundred rows.
    """
    if _is_postgres(session):
        similarity = func.similarity(Product.canonical_name, query)
        statement = (
            _listed_products()
            .where(*conditions, similarity > FUZZY_THRESHOLD)
            .order_by(similarity.desc())
            .limit(limit)
        )
        return list((await session.execute(statement)).all())

    candidates = (
        await session.execute(_listed_products().where(*conditions).limit(FUZZY_CANDIDATES * 4))
    ).all()
    normalized = canonicalize(query)
    scored = [
        (trigram_similarity(canonicalize(product.canonical_name), normalized), product, estimate)
        for product, estimate in candidates
    ]
    ranked = sorted(
        (item for item in scored if item[0] > FUZZY_THRESHOLD),
        key=lambda item: item[0],
        reverse=True,
    )
    return [(product, estimate) for _, product, estimate in ranked[:limit]]


async def load_product_detail(
    session: AsyncSession,
    product_id: UUID,
    *,
    now: datetime | None = None,
) -> ProductDetail | None:
    moment = now or datetime.now(timezone.utc)
    row = (
        await session.execute(_listed_products().where(Product.id == product_id))
    ).first()
    if row is None:
        return None

    product, estimate = row
    summary = product_summary(product, estimate.price_etb, estimate.confidence)
    return ProductDetail(
        **summary.model_dump(),
        barcode=product.barcode,
        price_range_etb=await _price_range(session, product_id, estimate.price_etb, now=moment),
        evidence_count=estimate.evidence_count,
        store_count=estimate.store_count,
        spread_pct=float(estimate.spread_pct),
        updated_at=as_utc(estimate.newest_observed_at),
        confidence_breakdown=ConfidenceBreakdown.model_validate(estimate.breakdown),
        sources=await _sources(session, product_id, now=moment),
        history=await _history(session, product_id, now=moment),
    )


async def _price_range(
    session: AsyncSession,
    product_id: UUID,
    market_price: Decimal,
    *,
    now: datetime,
) -> tuple[float, float]:
    """The middle half of what shoppers actually paid: the p25 and p75 prices."""
    observations = await load_observations(session, product_id, now=now)
    if not observations:
        return float(market_price), float(market_price)
    return (
        round(weighted_quantile(observations, 0.25), 2),
        round(weighted_quantile(observations, 0.75), 2),
    )


async def _sources(
    session: AsyncSession,
    product_id: UUID,
    *,
    now: datetime,
) -> list[SourceSummary]:
    rows = await session.execute(
        select(
            Evidence.source_type,
            func.count().label("count"),
            func.max(Evidence.observed_at).label("newest"),
        )
        .where(
            Evidence.product_id == product_id,
            Evidence.status == EvidenceStatus.ACCEPTED,
            Evidence.observed_at > now - timedelta(days=LOOKBACK_DAYS),
        )
        .group_by(Evidence.source_type)
        .order_by(func.count().desc())
    )
    return [
        SourceSummary(
            source_type=source.value,
            label=source_label(source),
            count=count,
            newest_observed_at=as_utc(newest),
        )
        for source, count, newest in rows
    ]


async def _history(
    session: AsyncSession,
    product_id: UUID,
    *,
    now: datetime,
) -> list[HistoryPoint]:
    rows = await session.scalars(
        select(PriceHistory)
        .where(
            PriceHistory.product_id == product_id,
            PriceHistory.day >= (now - timedelta(days=HISTORY_DAYS)).date(),
        )
        .order_by(PriceHistory.day)
    )
    return [
        HistoryPoint(
            day=row.day,
            price_etb=float(row.price_etb),
            evidence_count=row.evidence_count,
        )
        for row in rows
    ]


async def load_nearby_stores(
    session: AsyncSession,
    product_id: UUID,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_m: int = 5_000,
) -> NearbyStoresResponse | None:
    market = await session.scalar(
        select(PriceEstimate).where(
            PriceEstimate.product_id == product_id,
            PriceEstimate.store_id.is_(None),
        )
    )
    if market is None:
        return None

    carrying_stores = (
        select(Store, PriceEstimate)
        .join(PriceEstimate, PriceEstimate.store_id == Store.id)
        .where(PriceEstimate.product_id == product_id)
    )
    if latitude is not None and longitude is not None:
        distance = distance_expression(latitude, longitude)
        statement = (
            carrying_stores.add_columns(distance).where(distance <= radius_m).order_by(distance)
        )
    else:
        # Without a location there is nothing to sort by but the price.
        statement = carrying_stores.add_columns(null()).order_by(PriceEstimate.price_etb)

    market_price = float(market.price_etb)
    items = [
        NearbyStorePrice(
            id=store.id,
            name=store.name,
            district=store.district,
            kind=store.kind.value,
            latitude=store.latitude,
            longitude=store.longitude,
            price_etb=float(estimate.price_etb),
            confidence=estimate.confidence,
            updated_at=as_utc(estimate.newest_observed_at),
            distance_m=None if measured is None else round(measured),
            difference_from_market_etb=round(float(estimate.price_etb) - market_price, 2),
            verdict=verdict_for(float(estimate.price_etb), market_price),
        )
        for store, estimate, measured in (await session.execute(statement)).all()
    ]
    return NearbyStoresResponse(
        product_id=product_id,
        market_price_etb=market_price,
        items=items,
    )
