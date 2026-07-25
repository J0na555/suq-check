"""Fill an empty database with a demo-ready market.

Products and stores come from `data/*.csv`; the evidence is generated. Every
estimate and history row is produced by running the price engine over that
evidence, never by writing a price directly, so the seeded numbers are the same
numbers the ingest path would have produced.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import ColumnElement, delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.models.enums import EvidenceSource, EvidenceStatus
from app.models.evidence import Evidence
from app.models.price import PriceEstimate, PriceHistory
from app.models.product import Product, ProductAlias
from app.models.store import Store
from app.seed.catalog import Coverage, ProductRow, StoreRow, read_products, read_stores
from app.seed.generator import SEED_DAYS, GeneratedEvidence, generate_evidence, shelf_price
from app.services.normalize import canonicalize
from app.services.price_engine import LOOKBACK_DAYS, recompute_product
from app.services.verification import submit_evidence

# Deliberately unbelievable prices, submitted through the gate so the ingestion
# log opens on real pending and rejected decisions rather than invented ones.
OUTLIER_FACTORS = (0.35, 20.0, 1.7)


@dataclass(frozen=True, slots=True)
class SeedSummary:
    stores: int
    products: int
    aliases: int
    evidence: int
    pending: int
    rejected: int
    estimates: int
    history_days: int

    def lines(self) -> list[str]:
        return [
            f"{self.stores} stores, {self.products} products, {self.aliases} aliases",
            (
                f"{self.evidence} evidence rows "
                f"({self.pending} pending, {self.rejected} rejected by the gate)"
            ),
            f"{self.estimates} price estimates across {self.history_days} days of history",
        ]


async def seed_database(
    session: AsyncSession,
    *,
    products: Sequence[ProductRow] | None = None,
    stores: Sequence[StoreRow] | None = None,
    now: datetime | None = None,
    days: int = SEED_DAYS,
) -> SeedSummary:
    """Rebuild the catalog and every derived number. Flushes; never commits."""
    catalog = list(products) if products is not None else read_products()
    locations = list(stores) if stores is not None else read_stores()
    moment = now or datetime.now(timezone.utc)

    await _upsert_stores(session, locations)
    saved_products = await _upsert_products(session, catalog)
    aliases = await _remember_catalog_aliases(session, catalog)
    await _clear_generated(session)

    generated: list[GeneratedEvidence] = []
    for product in catalog:
        generated.extend(generate_evidence(product, locations, now=moment, days=days))
    await _insert_evidence(session, generated)

    # The engine only looks back thirty days, so history for the older half of
    # the window has to be recomputed as of a date inside it.
    for as_of in (moment - timedelta(days=LOOKBACK_DAYS), moment):
        for product in catalog:
            await recompute_product(session, product.id, now=as_of)

    await _submit_outliers(session, catalog, saved_products, locations, now=moment)
    return await _summarize(session, aliases=aliases)


async def _upsert_stores(session: AsyncSession, stores: Sequence[StoreRow]) -> None:
    existing = {
        row.id: row
        for row in await session.scalars(
            select(Store).where(Store.id.in_([store.id for store in stores]))
        )
    }
    for store in stores:
        row = existing.get(store.id) or Store(id=store.id)
        row.name = store.name
        row.chain = store.chain
        row.district = store.district
        row.latitude = store.latitude
        row.longitude = store.longitude
        row.kind = store.kind
        if store.id not in existing:
            session.add(row)
    await session.flush()


async def _upsert_products(
    session: AsyncSession,
    products: Sequence[ProductRow],
) -> dict[UUID, Product]:
    existing = {
        row.id: row
        for row in await session.scalars(
            select(Product).where(Product.id.in_([product.id for product in products]))
        )
    }
    saved: dict[UUID, Product] = {}
    for product in products:
        row = existing.get(product.id) or Product(id=product.id)
        row.canonical_name = product.canonical_name
        row.brand = product.brand
        row.category = product.category
        row.size_value = Decimal(str(product.size_value))
        row.size_unit = product.size_unit
        row.barcode = product.barcode
        if product.id not in existing:
            session.add(row)
        saved[product.id] = row
    await session.flush()
    return saved


async def _remember_catalog_aliases(
    session: AsyncSession,
    products: Sequence[ProductRow],
) -> int:
    """Give the normalizer something to match before the first receipt arrives."""
    taken = set(await session.scalars(select(ProductAlias.normalized_text)))
    added = 0
    for product in products:
        normalized = canonicalize(product.canonical_name)
        if not normalized or normalized in taken:
            continue
        session.add(
            ProductAlias(
                product_id=product.id,
                raw_text=product.canonical_name,
                normalized_text=normalized,
                source="seed",
            )
        )
        taken.add(normalized)
        added += 1
    await session.flush()
    return added


async def _clear_generated(session: AsyncSession) -> None:
    """The seed owns evidence and everything derived from it."""
    await session.execute(delete(PriceHistory))
    await session.execute(delete(PriceEstimate))
    await session.execute(delete(Evidence))
    await session.flush()


async def _insert_evidence(session: AsyncSession, generated: Sequence[GeneratedEvidence]) -> None:
    if not generated:
        return

    await session.execute(
        insert(Evidence),
        [
            {
                "id": uuid4(),
                "product_id": item.product_id,
                "store_id": item.store.id,
                "price_etb": Decimal(str(item.price_etb)),
                "source_type": item.source_type,
                "ocr_confidence": Decimal(str(item.ocr_confidence)),
                "observed_at": item.observed_at,
                "status": EvidenceStatus.ACCEPTED,
                "rejection_reason": None,
                "raw_payload": {"source": "seed"},
                # A report lands in the log a minute after it was observed, so
                # the dashboard reads as a stream rather than one bulk import.
                "created_at": item.observed_at + timedelta(minutes=1),
                "updated_at": item.observed_at + timedelta(minutes=1),
            }
            for item in generated
        ],
    )
    await session.flush()


async def _submit_outliers(
    session: AsyncSession,
    catalog: Sequence[ProductRow],
    saved: dict[UUID, Product],
    stores: Sequence[StoreRow],
    *,
    now: datetime,
) -> None:
    if not stores:
        return

    well_covered = [product for product in catalog if product.coverage is Coverage.RICH] or list(
        catalog
    )
    for index, factor in enumerate(OUTLIER_FACTORS):
        product = well_covered[index % len(well_covered)]
        market = await session.scalar(
            select(PriceEstimate.price_etb).where(
                PriceEstimate.product_id == product.id,
                PriceEstimate.store_id.is_(None),
            )
        )
        if market is None:
            continue

        await submit_evidence(
            session,
            product=saved[product.id],
            price_etb=shelf_price(float(market) * factor),
            source_type=EvidenceSource.COMMUNITY,
            observed_at=now - timedelta(minutes=8 * (index + 1)),
            store_id=stores[index % len(stores)].id,
            now=now,
        )


async def _count(
    session: AsyncSession,
    model: type[DeclarativeBase],
    *conditions: ColumnElement[bool],
) -> int:
    statement = select(func.count()).select_from(model)
    for condition in conditions:
        statement = statement.where(condition)
    return await session.scalar(statement) or 0


async def _summarize(session: AsyncSession, *, aliases: int) -> SeedSummary:
    history_days = await session.scalar(select(func.count(func.distinct(PriceHistory.day))))
    return SeedSummary(
        stores=await _count(session, Store),
        products=await _count(session, Product),
        aliases=aliases,
        evidence=await _count(session, Evidence),
        pending=await _count(session, Evidence, Evidence.status == EvidenceStatus.PENDING),
        rejected=await _count(session, Evidence, Evidence.status == EvidenceStatus.REJECTED),
        estimates=await _count(session, PriceEstimate),
        history_days=history_days or 0,
    )
