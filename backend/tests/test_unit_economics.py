"""Gemini token costing and the unit-economics read path."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.costing import (
    COST_BENCHMARKS,
    allocated_tokens,
    gemini_cost_usd,
    usd_to_etb,
)
from app.models.enums import EvidenceSource, EvidenceStatus
from app.models.evidence import Evidence
from app.repositories.analytics import load_unit_economics
from app.seed import read_products, read_stores


def test_gemini_cost_matches_list_prices() -> None:
    # 1M input + 1M output → $0.30 + $2.50
    assert gemini_cost_usd(prompt_tokens=1_000_000, candidates_tokens=1_000_000) == pytest.approx(2.8)
    assert usd_to_etb(20.0) == pytest.approx(3160.0)


def test_allocated_tokens_split_a_shared_call() -> None:
    assert allocated_tokens(250, shared_across=2) == 125.0
    assert allocated_tokens(250, shared_across=0) == 250.0


def test_four_benchmarks_include_wfp_and_modelled_suqcheck() -> None:
    ids = {item.id for item in COST_BENCHMARKS}
    assert ids == {
        "wfp_face_to_face",
        "field_agent_sa",
        "premise_capture",
        "suqcheck_modelled",
    }
    modelled = next(item for item in COST_BENCHMARKS if item.id == "suqcheck_modelled")
    assert modelled.min_etb == 5.9
    wfp = next(item for item in COST_BENCHMARKS if item.id == "wfp_face_to_face")
    assert (wfp.min_etb, wfp.max_etb) == (3160.0, 6320.0)


@pytest.mark.asyncio
async def test_unit_economics_prices_shared_gemini_usage(
    writable_session: AsyncSession,
) -> None:
    products = {product.canonical_name: product for product in read_products()}
    stores = {store.name: store for store in read_stores()}
    oil = products["Hayat Cooking Oil 1L"]
    sugar = products["Shega White Sugar 1kg"]
    store = stores["Selam Mart"]
    observed_at = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)

    shared = {
        "model": "gemini-2.5-flash",
        "prompt_token_count": 200,
        "candidates_token_count": 50,
        "total_token_count": 250,
        "shared_across_observations": 2,
    }
    for product, price in ((oil, 340.0), (sugar, 205.0)):
        writable_session.add(
            Evidence(
                product_id=product.id,
                store_id=store.id,
                price_etb=price,
                source_type=EvidenceSource.STORE_VISIT,
                ocr_confidence=0.9,
                observed_at=observed_at,
                status=EvidenceStatus.ACCEPTED,
                raw_payload={"gemini": shared, "device_id": "econ-test"},
            )
        )
    await writable_session.commit()

    result = await load_unit_economics(
        writable_session,
        period_days=30,
        now=datetime(2026, 7, 25, tzinfo=timezone.utc),
    )

    assert result.observations >= 2
    visit = next(item for item in result.by_source if item.source_type == "store_visit")
    # Two rows share one 200/50 call → 200 prompt and 50 candidates in total.
    assert visit.prompt_tokens == pytest.approx(200.0)
    assert visit.candidates_tokens == pytest.approx(50.0)
    expected_usd = gemini_cost_usd(prompt_tokens=200, candidates_tokens=50)
    assert visit.gemini_cost_etb == round(usd_to_etb(expected_usd), 4)
    assert any(item.id == "suqcheck_modelled" for item in result.benchmarks)


def test_unit_economics_reads_seeded_observations(database_client: TestClient) -> None:
    response = database_client.get("/api/analytics/unit-economics", params={"period_days": 60})

    assert response.status_code == 200
    body = response.json()
    assert body["period_days"] == 60
    assert body["observations"] > 0
    assert body["verified_observations"] > 0
    assert len(body["benchmarks"]) == 4
    assert body["usd_to_etb"] == 158.0
