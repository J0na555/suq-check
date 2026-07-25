"""The committed CSVs, the evidence generator, and what the seed leaves behind."""

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from itertools import pairwise
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Evidence, PriceEstimate, PriceHistory, Product, Store
from app.models.enums import (
    EvidenceSource,
    EvidenceStatus,
    ProductCategory,
    SizeUnit,
    StoreKind,
)
from app.seed import Coverage, SeedDataError, read_products, read_stores
from app.seed.catalog import product_id
from app.seed.generator import (
    PROFILES,
    SEED_DAYS,
    SKUS_PER_VISIT,
    VISIT_INTERVAL_DAYS,
    VISIT_WEEKS,
    generate_evidence,
    generate_store_visit_evidence,
    shelf_price,
)

NOW = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)
PRODUCTS = read_products()
STORES = read_stores()


def write_csv(path: Path, header: str, *rows: str) -> Path:
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    return path


PRODUCT_HEADER = (
    "canonical_name,brand,category,size_value,size_unit,barcode,base_price_etb,coverage"
)
STORE_HEADER = "name,chain,district,latitude,longitude,kind"


def test_the_committed_catalog_parses() -> None:
    assert len(PRODUCTS) == 40
    assert len(STORES) == 120
    assert {store.district for store in STORES} == {"Bole", "Yeka", "Arada"}
    assert all(
        sum(1 for store in STORES if store.district == district) == 40
        for district in ("Bole", "Yeka", "Arada")
    )
    assert {product.category for product in PRODUCTS} <= set(ProductCategory)
    assert {product.size_unit for product in PRODUCTS} <= set(SizeUnit)
    assert all(product.base_price_etb > 0 for product in PRODUCTS)
    samanu = {"Tena", "Chef Luca", "555", "Aura", "Astco", "Aquasafe"}
    assert sum(1 for product in PRODUCTS if product.brand in samanu) == 10


def test_every_researched_price_clears_the_gate_the_seed_will_face(
    migration_bounds: tuple[tuple[str, str, str, str], ...],
) -> None:
    """A base price outside its category bounds has the gate reject its own seed."""
    ranges = {
        (category, size_unit): (float(minimum), float(maximum))
        for category, size_unit, minimum, maximum in migration_bounds
    }

    for product in PRODUCTS:
        pack = (product.category.value, product.size_unit.value)
        assert pack in ranges, f"{product.canonical_name}: no bounds for {pack[0]}/{pack[1]}"
        low, high = ranges[pack]
        assert low <= product.base_price_etb <= high, (
            f"{product.canonical_name} at {product.base_price_etb} ETB "
            f"is outside the {low}-{high} ETB range the gate allows"
        )


def test_ids_are_derived_from_the_catalog_row_not_invented() -> None:
    oil = next(product for product in PRODUCTS if product.brand == "Hayat")

    assert oil.id == product_id("Hayat", "Hayat Cooking Oil 1L", 1, SizeUnit.LITER)
    assert oil.id == product_id("  hayat  ", "hayat cooking oil 1l", 1, SizeUnit.LITER)


def test_weekly_store_visits_cover_the_pitch_volume() -> None:
    visits = generate_store_visit_evidence(PRODUCTS, STORES, now=NOW)
    physical = [store for store in STORES if store.kind is not StoreKind.ONLINE]

    assert len(visits) == len(physical) * VISIT_WEEKS * SKUS_PER_VISIT
    assert {item.source_type for item in visits} == {EvidenceSource.STORE_VISIT}
    assert len({item.store.id for item in visits}) == len(physical)
    # Thin and stale stay out so the confidence screen still has a story.
    visited = {item.product_id for item in visits}
    for product in PRODUCTS:
        if product.coverage in (Coverage.THIN, Coverage.STALE):
            assert product.id not in visited
        else:
            assert product.id in visited
    again = generate_store_visit_evidence(PRODUCTS, STORES, now=NOW)
    assert [item.price_etb for item in visits] == [item.price_etb for item in again]


def test_a_shop_keeps_its_shelf_and_gets_visited_once_a_week() -> None:
    visits = generate_store_visit_evidence(PRODUCTS, STORES, now=NOW)

    shelves: dict[UUID, set[UUID]] = defaultdict(set)
    visit_days: dict[UUID, set[date]] = defaultdict(set)
    for item in visits:
        shelves[item.store.id].add(item.product_id)
        visit_days[item.store.id].add(item.observed_at.date())

    for store_id, days in visit_days.items():
        # One shelf, read whole, on each of `VISIT_WEEKS` days exactly a week apart.
        assert len(shelves[store_id]) == SKUS_PER_VISIT
        assert len(days) == VISIT_WEEKS
        ordered = sorted(days)
        gaps = {(later - earlier).days for earlier, later in pairwise(ordered)}
        assert gaps == {VISIT_INTERVAL_DAYS}

    # The city is not all visited on a Monday: the round fills the whole week.
    assert len({min(days).weekday() for days in visit_days.values()}) == VISIT_INTERVAL_DAYS


def test_a_blank_line_in_the_middle_is_skipped(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "products.csv",
        PRODUCT_HEADER,
        "Hayat Cooking Oil 1L,Hayat,cooking_oil,1,l,,340,rich",
        ",,,,,,,",
        "Shega White Sugar 1kg,Shega,sugar,1,kg,,205,normal",
    )

    assert len(read_products(path)) == 2


@pytest.mark.parametrize(
    ("row", "message"),
    [
        ("Oil,Hayat,olive_oil,1,l,,340,rich", "category is 'olive_oil'"),
        ("Oil,Hayat,cooking_oil,1,gallon,,340,rich", "size_unit is 'gallon'"),
        ("Oil,Hayat,cooking_oil,1,l,,340,plenty", "coverage is 'plenty'"),
        ("Oil,Hayat,cooking_oil,1,l,,cheap,rich", "base_price_etb must be a number"),
        ("Oil,Hayat,cooking_oil,0,l,,340,rich", "size_value must be above zero"),
        ("Oil,Hayat,cooking_oil,1,l,,0,rich", "base_price_etb must be above zero"),
        (",Hayat,cooking_oil,1,l,,340,rich", "canonical_name is required"),
    ],
)
def test_a_bad_product_row_names_the_row_and_the_column(
    tmp_path: Path,
    row: str,
    message: str,
) -> None:
    path = write_csv(tmp_path / "products.csv", PRODUCT_HEADER, row)

    with pytest.raises(SeedDataError) as error:
        read_products(path)

    assert "row 2" in str(error.value)
    assert message in str(error.value)


def test_a_missing_column_is_reported_before_any_row(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "products.csv", "canonical_name,brand", "Oil,Hayat")

    with pytest.raises(SeedDataError, match="missing the category"):
        read_products(path)


def test_a_missing_file_says_which_one(tmp_path: Path) -> None:
    with pytest.raises(SeedDataError, match="does not exist"):
        read_products(tmp_path / "nope.csv")


def test_the_same_product_listed_twice_is_refused(tmp_path: Path) -> None:
    row = "Hayat Cooking Oil 1L,Hayat,cooking_oil,1,l,,340,rich"
    path = write_csv(tmp_path / "products.csv", PRODUCT_HEADER, row, row)

    with pytest.raises(SeedDataError, match="same product twice"):
        read_products(path)


def test_an_impossible_coordinate_is_refused(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "stores.csv",
        STORE_HEADER,
        "Selam Mart,,Piassa,91.0,38.75,shop",
    )

    with pytest.raises(SeedDataError, match="not a valid coordinate"):
        read_stores(path)


def test_generated_evidence_is_reproducible() -> None:
    oil = next(product for product in PRODUCTS if product.brand == "Hayat")

    first = generate_evidence(oil, STORES, now=NOW)
    second = generate_evidence(oil, STORES, now=NOW)

    assert [item.price_etb for item in first] == [item.price_etb for item in second]
    assert [item.store.id for item in first] == [item.store.id for item in second]


def test_generated_prices_look_like_shelf_prices() -> None:
    for product in PRODUCTS:
        for item in generate_evidence(product, STORES, now=NOW):
            assert item.price_etb == shelf_price(item.price_etb)
            assert 0 < item.price_etb
            assert 0 < item.ocr_confidence <= 1
            assert item.observed_at <= NOW


def test_coverage_decides_how_wide_and_how_recent_the_evidence_is() -> None:
    by_coverage = {}
    for coverage in Coverage:
        product = next(item for item in PRODUCTS if item.coverage is coverage)
        generated = generate_evidence(product, STORES, now=NOW)
        by_coverage[coverage] = generated

        stores = {item.store.id for item in generated}
        assert len(stores) <= PROFILES[coverage].stores
        oldest = min(item.observed_at for item in generated)
        assert oldest >= NOW - timedelta(days=SEED_DAYS)

    newest_stale = max(item.observed_at for item in by_coverage[Coverage.STALE])
    newest_rich = max(item.observed_at for item in by_coverage[Coverage.RICH])
    assert newest_stale < NOW - timedelta(days=12)
    assert newest_rich > NOW - timedelta(days=1)
    assert len(by_coverage[Coverage.RICH]) > len(by_coverage[Coverage.THIN])


@pytest.mark.parametrize(
    ("category", "expected_rise"),
    [(ProductCategory.COOKING_OIL, True), (ProductCategory.SUGAR, False)],
)
def test_the_seeded_trends_move_in_the_intended_direction(
    category: ProductCategory,
    expected_rise: bool,
) -> None:
    product = next(item for item in PRODUCTS if item.category is category)
    generated = sorted(
        generate_evidence(product, STORES, now=NOW), key=lambda item: item.observed_at
    )
    first_week = [item.price_etb for item in generated[:20]]
    last_week = [item.price_etb for item in generated[-20:]]
    rose = sum(last_week) / len(last_week) > sum(first_week) / len(first_week)

    assert rose is expected_rise


@pytest.mark.asyncio
async def test_the_seed_prices_every_product_through_the_engine(session: AsyncSession) -> None:
    products = list(await session.scalars(select(Product)))
    stores = list(await session.scalars(select(Store)))

    assert len(products) == len(PRODUCTS)
    assert len(stores) == len(STORES)

    for product in products:
        market = await session.scalar(
            select(PriceEstimate).where(
                PriceEstimate.product_id == product.id,
                PriceEstimate.store_id.is_(None),
            )
        )
        assert market is not None, product.canonical_name
        assert market.price_etb > 0
        assert market.breakdown["factors"]
        assert market.evidence_count > 0


@pytest.mark.asyncio
async def test_a_full_round_of_weekly_visits_reaches_the_database(
    session: AsyncSession,
) -> None:
    """The seed runs the visit pass too, not only the per-product walk."""
    physical = [store for store in STORES if store.kind is not StoreKind.ONLINE]
    cells_this_week = await session.scalar(
        select(func.count())
        .select_from(Evidence)
        .where(
            Evidence.source_type == EvidenceSource.STORE_VISIT,
            Evidence.observed_at > NOW - timedelta(days=VISIT_INTERVAL_DAYS),
        )
    )

    assert cells_this_week >= len(physical) * SKUS_PER_VISIT


@pytest.mark.asyncio
async def test_history_covers_the_whole_window_not_just_the_lookback(
    session: AsyncSession,
) -> None:
    span = await session.execute(select(func.min(PriceHistory.day), func.max(PriceHistory.day)))
    oldest, newest = span.one()

    assert isinstance(oldest, date)
    assert (newest - oldest).days >= SEED_DAYS - 2


@pytest.mark.asyncio
async def test_the_seed_ends_with_real_gate_decisions_to_show(session: AsyncSession) -> None:
    counts = {
        status: await session.scalar(
            select(func.count()).select_from(Evidence).where(Evidence.status == status)
        )
        for status in EvidenceStatus
    }

    assert counts[EvidenceStatus.ACCEPTED] > 100
    assert counts[EvidenceStatus.PENDING] >= 1
    assert counts[EvidenceStatus.REJECTED] >= 1

    unaccepted = await session.scalars(
        select(Evidence).where(Evidence.status != EvidenceStatus.ACCEPTED)
    )
    for row in unaccepted:
        assert row.rejection_reason
        assert "ETB" in row.rejection_reason


@pytest.mark.asyncio
async def test_confidence_spans_low_medium_and_high(session: AsyncSession) -> None:
    scores = list(
        await session.scalars(
            select(PriceEstimate.confidence).where(PriceEstimate.store_id.is_(None))
        )
    )

    assert max(scores) >= 85
    assert min(scores) < 65
    assert any(65 <= score < 85 for score in scores)
