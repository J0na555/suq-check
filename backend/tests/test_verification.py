from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base, CategoryPriceBounds, Evidence, PriceEstimate, Product, Store
from app.models.enums import (
    EvidenceSource,
    EvidenceStatus,
    ProductCategory,
    SizeUnit,
    StoreKind,
)
from app.services.verification import (
    EstimateSnapshot,
    PriceBounds,
    decide,
    submit_evidence,
)

NOW = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)
OIL_BOUNDS = PriceBounds(min_etb=90, max_etb=3000)
OIL_ESTIMATE = EstimateSnapshot(price_etb=340, confidence=98)


def gate(price: float, *, estimate: EstimateSnapshot | None = OIL_ESTIMATE):
    return decide(
        price,
        category=ProductCategory.COOKING_OIL,
        size_unit=SizeUnit.LITER,
        bounds=OIL_BOUNDS,
        estimate=estimate,
    )


def test_price_outside_the_category_bounds_is_rejected_before_anything_else() -> None:
    decision = gate(4200)

    assert decision.status == EvidenceStatus.REJECTED
    assert decision.reason == (
        "4200 ETB is outside the 90-3000 ETB range recorded for cooking oil sold by the litre."
    )


def test_bounds_are_inclusive() -> None:
    assert "outside" not in gate(90).reason
    assert "outside" not in gate(3000).reason
    assert gate(89).reason.startswith("89 ETB is outside")


def test_agreeing_price_is_accepted() -> None:
    decision = gate(350)

    assert decision.status == EvidenceStatus.ACCEPTED
    assert decision.reason == "Price agrees with the 340 ETB market estimate within 2.9%."


def test_deviation_just_under_forty_percent_still_accepts() -> None:
    decision = gate(475)

    assert decision.status == EvidenceStatus.ACCEPTED


def test_deviation_at_forty_percent_pends() -> None:
    decision = gate(476)

    assert decision.status == EvidenceStatus.PENDING


def test_the_demo_outlier_lands_in_pending_with_a_readable_reason() -> None:
    decision = gate(120)

    assert decision.status == EvidenceStatus.PENDING
    assert decision.reason == (
        "Price is 64.7% below the 340 ETB market estimate and needs verification."
    )


def test_deviation_at_one_hundred_fifty_percent_still_pends() -> None:
    decision = gate(850)

    assert decision.status == EvidenceStatus.PENDING


def test_deviation_above_one_hundred_fifty_percent_is_rejected() -> None:
    decision = gate(855)

    assert decision.status == EvidenceStatus.REJECTED
    assert "far beyond what verification can explain" in decision.reason


def test_a_low_confidence_estimate_does_not_gate_anything() -> None:
    decision = gate(120, estimate=EstimateSnapshot(price_etb=340, confidence=59))

    assert decision.status == EvidenceStatus.ACCEPTED
    assert decision.reason == (
        "No verified estimate exists yet, so this report bootstraps the price."
    )


def test_the_first_report_for_a_product_bootstraps_the_estimate() -> None:
    decision = gate(340, estimate=None)

    assert decision.status == EvidenceStatus.ACCEPTED


def test_missing_bounds_do_not_block_ingestion() -> None:
    decision = decide(
        4200,
        category=ProductCategory.COOKING_OIL,
        size_unit=SizeUnit.LITER,
        bounds=None,
        estimate=None,
    )

    assert decision.status == EvidenceStatus.ACCEPTED


@pytest.mark.asyncio
async def test_accepted_submission_recomputes_and_pending_one_does_not() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        product = Product(
            canonical_name="Hayat Cooking Oil 1L",
            brand="Hayat",
            category=ProductCategory.COOKING_OIL,
            size_value=1,
            size_unit=SizeUnit.LITER,
        )
        store = Store(
            name="Selam Mart",
            district="Piassa",
            latitude=9.03,
            longitude=38.75,
            kind=StoreKind.SUPERMARKET,
        )
        session.add_all(
            [
                product,
                store,
                CategoryPriceBounds(
                    category=ProductCategory.COOKING_OIL,
                    size_unit=SizeUnit.LITER,
                    min_etb=90,
                    max_etb=3000,
                ),
            ]
        )
        await session.flush()

        for offset, price in enumerate((340, 338, 342, 339)):
            _, decision = await submit_evidence(
                session,
                product=product,
                price_etb=price,
                source_type=EvidenceSource.RECEIPT,
                observed_at=NOW - timedelta(hours=offset),
                store_id=store.id,
                now=NOW,
            )
            assert decision.status == EvidenceStatus.ACCEPTED

        outlier, outlier_decision = await submit_evidence(
            session,
            product=product,
            price_etb=120,
            source_type=EvidenceSource.COMMUNITY,
            observed_at=NOW,
            store_id=store.id,
            now=NOW,
        )
        absurd, absurd_decision = await submit_evidence(
            session,
            product=product,
            price_etb=4200,
            source_type=EvidenceSource.COMMUNITY,
            observed_at=NOW,
            store_id=store.id,
            now=NOW,
        )

        market = await session.scalar(
            select(PriceEstimate).where(
                PriceEstimate.product_id == product.id,
                PriceEstimate.store_id.is_(None),
            )
        )
        accepted = list(
            await session.scalars(
                select(Evidence).where(
                    Evidence.product_id == product.id,
                    Evidence.status == EvidenceStatus.ACCEPTED,
                )
            )
        )

    assert outlier_decision.status == EvidenceStatus.PENDING
    assert outlier.rejection_reason == outlier_decision.reason
    assert absurd_decision.status == EvidenceStatus.REJECTED
    assert absurd.status == EvidenceStatus.REJECTED
    assert len(accepted) == 4
    assert market is not None
    assert 338 <= float(market.price_etb) <= 341
    assert market.evidence_count == 4

    await engine.dispose()
