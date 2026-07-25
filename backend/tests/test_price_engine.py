from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base, Evidence, PriceEstimate, PriceHistory, Product, Store
from app.models.enums import (
    EvidenceSource,
    EvidenceStatus,
    ProductCategory,
    SizeUnit,
    StoreKind,
)
from app.services.price_engine import (
    Observation,
    WeightedObservation,
    agreement_score,
    diversity_score,
    estimate,
    freshness_score,
    freshness_weight,
    recompute_product,
    spread,
    volume_score,
    weigh,
    weigh_all,
    weighted_median,
    weighted_quantile,
)

NOW = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)


def flat(*prices: float, weight: float = 1.0, freshness: float = 1.0) -> list[WeightedObservation]:
    return [
        WeightedObservation(
            price_etb=price,
            weight=weight,
            freshness=freshness,
            observed_at=NOW - timedelta(hours=index),
            store_id=uuid4(),
        )
        for index, price in enumerate(prices)
    ]


def test_weighted_median_ignores_a_single_fat_fingered_entry() -> None:
    observations = flat(330, 335, 340, 345, 12_000)

    assert weighted_median(observations) == 340


def test_weighted_median_follows_the_weight_not_the_count() -> None:
    trusted = WeightedObservation(
        price_etb=340,
        weight=9.0,
        freshness=1.0,
        observed_at=NOW,
        store_id=uuid4(),
    )
    noise = flat(120, 125, weight=0.1)

    assert weighted_median([trusted, *noise]) > 330


def test_weighted_median_of_two_equal_weights_is_the_midpoint() -> None:
    assert weighted_median(flat(330, 350)) == pytest.approx(340)


def test_spread_is_the_interquartile_range_over_the_median() -> None:
    observations = flat(300, 320, 340, 360, 380)

    assert weighted_quantile(observations, 0.25) == pytest.approx(315)
    assert weighted_quantile(observations, 0.75) == pytest.approx(365)
    assert spread(observations) == pytest.approx(50 / 340)
    assert spread(flat(340, 340, 340)) == 0.0


def test_freshness_weight_halves_every_seven_days() -> None:
    assert freshness_weight(NOW - timedelta(days=7), NOW) == pytest.approx(0.5)
    assert freshness_weight(NOW - timedelta(days=14), NOW) == pytest.approx(0.25)


def test_source_weight_and_ocr_confidence_multiply_into_the_weight() -> None:
    observation = Observation(
        price_etb=340,
        source_type=EvidenceSource.COMMUNITY,
        observed_at=NOW - timedelta(days=7),
        ocr_confidence=0.5,
    )

    assert weigh(observation, NOW).weight == pytest.approx(0.4 * 0.5 * 0.5)


def test_evidence_older_than_the_lookback_is_dropped() -> None:
    inside = Observation(340, EvidenceSource.RECEIPT, NOW - timedelta(days=29))
    outside = Observation(120, EvidenceSource.RECEIPT, NOW - timedelta(days=31))

    assert [item.price_etb for item in weigh_all([inside, outside], NOW)] == [340]


def test_volume_score_saturates_at_eight_units_of_weight() -> None:
    assert volume_score(flat(340, 340, 340, 340)) == pytest.approx(0.7325, abs=1e-4)
    assert volume_score(flat(*[340] * 9)) == 1.0


def test_agreement_score_falls_to_zero_at_a_quarter_spread() -> None:
    assert agreement_score(0.0) == 1.0
    assert agreement_score(0.05) == pytest.approx(0.8)
    assert agreement_score(0.25) == 0.0
    assert agreement_score(0.60) == 0.0


def test_freshness_score_takes_the_newest_observation() -> None:
    observations = [
        WeightedObservation(340, 0.2, 0.2, NOW - timedelta(days=14)),
        WeightedObservation(345, 0.9, 0.9, NOW - timedelta(days=1)),
    ]

    assert freshness_score(observations) == pytest.approx(0.9)


def test_diversity_score_counts_stores_for_market_and_reports_for_a_store() -> None:
    market = flat(330, 340, 350)
    single_store = [
        WeightedObservation(340, 1.0, 1.0, NOW),
        WeightedObservation(342, 1.0, 1.0, NOW),
    ]

    assert diversity_score(market, "market") == 1.0
    assert diversity_score(market[:1], "market") == pytest.approx(1 / 3)
    assert diversity_score(single_store, "store") == 1.0


def test_agreeing_fresh_evidence_scores_high_and_explains_itself() -> None:
    observations = [
        weigh(
            Observation(
                price_etb=price,
                source_type=EvidenceSource.RECEIPT,
                observed_at=NOW - timedelta(minutes=37),
                store_id=uuid4(),
            ),
            NOW,
        )
        for price in (336, 338, 340, 342, 344, 340, 339, 341, 340, 340, 337, 343)
    ]

    result = estimate(observations, now=NOW)

    assert result is not None
    assert result.confidence >= 85
    assert result.breakdown.band == "high"
    assert result.breakdown.score == result.confidence
    assert [factor.name for factor in result.breakdown.factors] == [
        "volume",
        "agreement",
        "freshness",
        "diversity",
    ]
    assert sum(factor.weight for factor in result.breakdown.factors) == pytest.approx(1.0)
    assert result.breakdown.factors[0].detail == "12 accepted reports"
    assert result.breakdown.capped is False


def test_stale_evidence_is_capped_at_sixty_with_a_reason() -> None:
    observations = [
        weigh(
            Observation(
                price_etb=340,
                source_type=EvidenceSource.PARTNER,
                observed_at=NOW - timedelta(days=13),
                store_id=uuid4(),
            ),
            NOW,
        )
        for _ in range(12)
    ]

    result = estimate(observations, now=NOW)

    assert result is not None
    assert result.confidence == 60
    assert result.breakdown.capped is True
    assert result.breakdown.cap_reason is not None
    assert "capped at 60" in result.breakdown.cap_reason


def test_the_cap_never_raises_a_low_score() -> None:
    observations = [
        weigh(
            Observation(
                price_etb=340,
                source_type=EvidenceSource.COMMUNITY,
                observed_at=NOW - timedelta(days=25),
                ocr_confidence=0.6,
            ),
            NOW,
        )
    ]

    result = estimate(observations, now=NOW)

    assert result is not None
    assert result.confidence < 60
    assert result.breakdown.capped is False
    assert result.breakdown.band == "low"


def test_estimate_of_nothing_is_none() -> None:
    assert estimate([], now=NOW) is None


@pytest.mark.asyncio
async def test_recompute_writes_market_store_and_history_rows() -> None:
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
        stores = [
            Store(
                name=name,
                district="Piassa",
                latitude=9.03,
                longitude=38.75,
                kind=StoreKind.SUPERMARKET,
            )
            for name in ("Selam Mart", "Abebe Shop")
        ]
        session.add_all([product, *stores])
        await session.flush()

        session.add_all(
            [
                Evidence(
                    product_id=product.id,
                    store_id=stores[index % 2].id,
                    price_etb=price,
                    source_type=EvidenceSource.RECEIPT,
                    ocr_confidence=1,
                    observed_at=NOW - timedelta(days=index),
                    status=EvidenceStatus.ACCEPTED,
                    raw_payload={},
                )
                for index, price in enumerate((340, 338, 336, 334))
            ]
        )
        session.add(
            Evidence(
                product_id=product.id,
                store_id=stores[0].id,
                price_etb=120,
                source_type=EvidenceSource.COMMUNITY,
                ocr_confidence=1,
                observed_at=NOW,
                status=EvidenceStatus.PENDING,
                raw_payload={},
            )
        )
        await session.flush()

        market = await recompute_product(session, product.id, now=NOW)

        estimates = list(
            await session.scalars(
                select(PriceEstimate).where(PriceEstimate.product_id == product.id)
            )
        )
        history = list(
            await session.scalars(
                select(PriceHistory)
                .where(PriceHistory.product_id == product.id)
                .order_by(PriceHistory.day)
            )
        )

    assert market is not None
    assert market.evidence_count == 4
    assert market.store_count == 2
    assert 330 < market.price_etb < 342
    assert {row.store_id for row in estimates} == {None, stores[0].id, stores[1].id}
    market_row = next(row for row in estimates if row.store_id is None)
    assert market_row.breakdown["factors"][0]["name"] == "volume"
    assert market_row.confidence == market.confidence
    assert [row.evidence_count for row in history] == [1, 1, 1, 1]

    await engine.dispose()
