"""Invent sixty days of plausible evidence for a catalog row.

Deterministic: the random stream is seeded from the product id (or store id for
the weekly visit pass), so re-running the seed reproduces the same prices and
the demo tells the same story twice. Nothing here touches the database or
decides a confidence score; the engine does that from the rows this module
returns.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from random import Random
from uuid import UUID

from app.models.enums import EvidenceSource, ProductCategory, StoreKind
from app.seed.catalog import Coverage, ProductRow, StoreRow

SEED_DAYS = 60

# One ambassador visit per store per week for eight weeks, reading ~28 SKUs from
# the posted price list. Across 119 physical shops that is about 3,300 priced
# cells a week, which is the number the cost-per-observation story rests on.
VISIT_WEEKS = 8
VISIT_INTERVAL_DAYS = 7
SKUS_PER_VISIT = 28

# Cooking oil climbing and sugar easing off give Market Pulse real movers
# instead of noise. Expressed as the total drift across the whole window.
CATEGORY_DRIFT: dict[ProductCategory, float] = {
    ProductCategory.COOKING_OIL: 0.18,
    ProductCategory.SUGAR: -0.09,
}

DAILY_NOISE = 0.004
PER_REPORT_NOISE = 0.006
LEVEL_FLOOR = 0.72
LEVEL_CEILING = 1.30
STORE_MULTIPLIER = (0.92, 1.08)

SOURCE_MIX: tuple[tuple[EvidenceSource, float], ...] = (
    (EvidenceSource.RECEIPT, 0.40),
    (EvidenceSource.STORE_VISIT, 0.20),
    (EvidenceSource.SHELF_PHOTO, 0.18),
    (EvidenceSource.COMMUNITY, 0.17),
    (EvidenceSource.PARTNER, 0.05),
)
OCR_CONFIDENCE: dict[EvidenceSource, tuple[float, float]] = {
    EvidenceSource.RECEIPT: (0.86, 0.99),
    EvidenceSource.SHELF_PHOTO: (0.80, 0.97),
    EvidenceSource.STORE_VISIT: (0.90, 0.99),
}


@dataclass(frozen=True, slots=True)
class CoverageProfile:
    """How widely and how recently a product gets reported."""

    stores: int
    reports_per_day: float
    quiet_days: int


PROFILES: dict[Coverage, CoverageProfile] = {
    Coverage.RICH: CoverageProfile(stores=6, reports_per_day=2.0, quiet_days=0),
    Coverage.NORMAL: CoverageProfile(stores=4, reports_per_day=0.9, quiet_days=0),
    Coverage.THIN: CoverageProfile(stores=2, reports_per_day=0.5, quiet_days=1),
    # Enough evidence to score well on everything except recency, which is what
    # makes the staleness cap visible instead of academic.
    Coverage.STALE: CoverageProfile(stores=4, reports_per_day=2.0, quiet_days=13),
}


@dataclass(frozen=True, slots=True)
class GeneratedEvidence:
    product_id: UUID
    store: StoreRow
    price_etb: float
    source_type: EvidenceSource
    ocr_confidence: float
    observed_at: datetime


def _report_count(rate: float, rng: Random) -> int:
    """Turn a fractional daily rate into a whole number of reports."""
    whole = int(rate)
    return whole + (1 if rng.random() < rate - whole else 0)


def _pick_source(store: StoreRow, rng: Random) -> EvidenceSource:
    if store.kind is StoreKind.ONLINE:
        return EvidenceSource.SCRAPE
    sources = [source for source, _ in SOURCE_MIX]
    weights = [weight for _, weight in SOURCE_MIX]
    return rng.choices(sources, weights=weights, k=1)[0]


def _ocr_confidence(source: EvidenceSource, rng: Random) -> float:
    low, high = OCR_CONFIDENCE.get(source, (1.0, 1.0))
    return round(rng.uniform(low, high), 4)


def _observed_at(now: datetime, age_days: int, rng: Random) -> datetime:
    if age_days == 0:
        return now - timedelta(minutes=rng.randint(15, 600))
    day = now - timedelta(days=age_days)
    return day.replace(
        hour=rng.randint(8, 18),
        minute=rng.randint(0, 59),
        second=0,
        microsecond=0,
    )


def shelf_price(value: float) -> float:
    """Round to the half birr a real price tag would show."""
    return round(value * 2) / 2


def _level_at(product: ProductRow, *, age_days: int, days: int) -> float:
    """Price level so age_days=0 sits at the researched base price."""
    drift = CATEGORY_DRIFT.get(product.category, 0.0)
    step = (1 + drift) ** (1 / days)
    level = (1 / (1 + drift)) * (step ** (days - age_days))
    return min(max(level, LEVEL_FLOOR), LEVEL_CEILING)


def _visit_basket(products: Sequence[ProductRow], rng: Random) -> list[ProductRow]:
    """Pick the SKUs a visit would photograph, leaving thin/stale for the walk."""
    tracked = [
        product
        for product in products
        if product.coverage not in (Coverage.THIN, Coverage.STALE)
    ]
    if not tracked:
        tracked = list(products)
    count = min(SKUS_PER_VISIT, len(tracked))
    return rng.sample(tracked, count)


def generate_evidence(
    product: ProductRow,
    stores: Sequence[StoreRow],
    *,
    now: datetime,
    days: int = SEED_DAYS,
) -> list[GeneratedEvidence]:
    """Walk a price from `days` ago to now, reporting it from a few stores."""
    if not stores:
        return []

    profile = PROFILES[product.coverage]
    rng = Random(f"{product.id}")
    carriers = rng.sample(list(stores), min(profile.stores, len(stores)))
    multipliers = {store.id: rng.uniform(*STORE_MULTIPLIER) for store in carriers}
    drift = CATEGORY_DRIFT.get(product.category, 0.0)
    step = (1 + drift) ** (1 / days)

    # The walk ends at the researched price, so `base_price_etb` stays what the
    # CSV promises: what the product costs today, not sixty days ago.
    level = 1 / (1 + drift)
    generated: list[GeneratedEvidence] = []
    for age_days in range(days - 1, -1, -1):
        level *= step * (1 + rng.gauss(0, DAILY_NOISE))
        level = min(max(level, LEVEL_FLOOR), LEVEL_CEILING)
        if age_days < profile.quiet_days:
            continue

        for _ in range(_report_count(profile.reports_per_day, rng)):
            store = rng.choice(carriers)
            source = _pick_source(store, rng)
            price = (
                product.base_price_etb
                * level
                * multipliers[store.id]
                * (1 + rng.gauss(0, PER_REPORT_NOISE))
            )
            generated.append(
                GeneratedEvidence(
                    product_id=product.id,
                    store=store,
                    price_etb=shelf_price(price),
                    source_type=source,
                    ocr_confidence=_ocr_confidence(source, rng),
                    observed_at=_observed_at(now, age_days, rng),
                )
            )

    return generated


def generate_store_visit_evidence(
    products: Sequence[ProductRow],
    stores: Sequence[StoreRow],
    *,
    now: datetime,
    days: int = SEED_DAYS,
    weeks: int = VISIT_WEEKS,
) -> list[GeneratedEvidence]:
    """One weekly store visit per shop for `weeks`, photographing ~28 SKUs each.

    Runs alongside the product-centric walk. Thin and stale products stay out of
    the visit basket so their coverage profiles still read on the confidence
    screen.
    """
    if not products or not stores:
        return []

    # Nobody walks into a website, so online sellers sit this pass out.
    physical = [store for store in stores if store.kind is not StoreKind.ONLINE]
    generated: list[GeneratedEvidence] = []
    for store in physical:
        rng = Random(f"visit:{store.id}")
        multiplier = rng.uniform(*STORE_MULTIPLIER)
        # A shop keeps the same shelf and the same visiting day week to week, so
        # the round reads as a hundred-odd visits spread across the week rather
        # than every ambassador in the city reporting on the same Monday.
        basket = _visit_basket(products, rng)
        weekday = rng.randrange(VISIT_INTERVAL_DAYS)
        for week in range(weeks):
            age_days = weekday + week * VISIT_INTERVAL_DAYS
            if age_days >= days:
                break

            observed = _observed_at(now, age_days, rng)
            for product in basket:
                level = _level_at(product, age_days=age_days, days=days)
                price = (
                    product.base_price_etb
                    * level
                    * multiplier
                    * (1 + rng.gauss(0, PER_REPORT_NOISE))
                )
                generated.append(
                    GeneratedEvidence(
                        product_id=product.id,
                        store=store,
                        price_etb=shelf_price(price),
                        source_type=EvidenceSource.STORE_VISIT,
                        ocr_confidence=_ocr_confidence(EvidenceSource.STORE_VISIT, rng),
                        observed_at=observed,
                    )
                )

    return generated
