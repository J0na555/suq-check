"""One store, priced against the market it sits in."""

from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EvidenceStatus
from app.models.evidence import Evidence
from app.models.price import PriceEstimate
from app.models.store import Store
from app.repositories.mappers import as_utc
from app.schemas.products import StoreDetail
from app.services.normalize import canonicalize, trigram_similarity

MARKET_INDEX_BASE = 100.0

# Receipts print store names loosely ("SELAM MART PIASSA"), so a name only has to
# be close to count as the same shop.
STORE_NAME_THRESHOLD = 0.40

_MARKET = PriceEstimate.__table__.alias("market")

# One store price divided by its product's market price. Averaging this over a
# store gives the store's index; averaging it over a district ranks districts.
PRICE_RATIO = PriceEstimate.price_etb / _MARKET.c.price_etb


def store_prices_against_market(*columns: ColumnElement[Any]) -> Select[Any]:
    """Every per-store estimate joined to the market estimate of the same product."""
    return (
        select(*columns)
        .select_from(PriceEstimate)
        .join(Store, Store.id == PriceEstimate.store_id)
        .join(
            _MARKET,
            (_MARKET.c.product_id == PriceEstimate.product_id) & _MARKET.c.store_id.is_(None),
        )
        .where(_MARKET.c.price_etb > 0)
    )


def as_price_index(ratio: float | None) -> float:
    return MARKET_INDEX_BASE if ratio is None else round(float(ratio) * MARKET_INDEX_BASE, 1)


async def load_store_detail(session: AsyncSession, store_id: UUID) -> StoreDetail | None:
    store = await session.get(Store, store_id)
    if store is None:
        return None

    product_count = await session.scalar(
        select(func.count())
        .select_from(PriceEstimate)
        .where(PriceEstimate.store_id == store_id)
    )
    last_reported_at = await session.scalar(
        select(func.max(Evidence.observed_at)).where(
            Evidence.store_id == store_id,
            Evidence.status == EvidenceStatus.ACCEPTED,
        )
    )
    ratio = await session.scalar(
        store_prices_against_market(func.avg(PRICE_RATIO)).where(
            PriceEstimate.store_id == store_id
        )
    )

    return StoreDetail(
        id=store.id,
        name=store.name,
        district=store.district,
        kind=store.kind.value,
        latitude=store.latitude,
        longitude=store.longitude,
        product_count=product_count or 0,
        average_price_index=as_price_index(ratio),
        # A store nobody has reported from yet still belongs in the catalog, so
        # fall back to when it was added rather than hiding it.
        last_reported_at=as_utc(last_reported_at or store.created_at),
    )


async def find_store_by_name(session: AsyncSession, name: str | None) -> Store | None:
    """Match the shop name printed on a receipt to a store in the catalog."""
    if not name or not name.strip():
        return None

    wanted = canonicalize(name)
    exact = await session.scalar(
        select(Store).where(func.lower(Store.name) == name.strip().lower())
    )
    if exact is not None:
        return exact

    scored = [
        (trigram_similarity(canonicalize(store.name), wanted), store)
        for store in await session.scalars(select(Store))
    ]
    if not scored:
        return None
    similarity, closest = max(scored, key=lambda item: item[0])
    return closest if similarity >= STORE_NAME_THRESHOLD else None
