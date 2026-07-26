"""Market Insights: MRP compliance, OOS ingest, and CSV export."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EvidenceSource
from app.repositories.insights import compliance_band
from app.seed import read_products, read_stores
from app.services.verification import submit_oos_evidence
from conftest import SEED_NOW

PRODUCTS = {product.canonical_name: product for product in read_products()}
STORES = {store.name: store for store in read_stores()}
OIL = PRODUCTS["Hayat Cooking Oil 1L"]
SELAM = STORES["Selam Mart"]


def test_compliance_band_tolerance() -> None:
    assert compliance_band(100, 100) == "at"
    assert compliance_band(101.5, 100) == "at"
    assert compliance_band(103, 100) == "above"
    assert compliance_band(97, 100) == "below"


def test_compliance_endpoint_returns_summary(database_client: TestClient) -> None:
    response = database_client.get("/api/analytics/compliance")

    assert response.status_code == 200
    body = response.json()
    summary = body["summary"]
    assert summary["shops_priced"] > 0
    assert summary["at_pct"] + summary["above_pct"] + summary["below_pct"] == round(
        summary["at_pct"] + summary["above_pct"] + summary["below_pct"], 1
    )
    assert body["items"]
    first = body["items"][0]
    assert first["mrp_etb"] > 0
    assert first["band"] in {"at", "above", "below"}


def test_districts_and_competitors_endpoints(database_client: TestClient) -> None:
    districts = database_client.get("/api/analytics/districts")
    assert districts.status_code == 200
    assert districts.json()["items"]

    competitors = database_client.get(
        "/api/analytics/competitors",
        params={"category": "cooking_oil"},
    )
    assert competitors.status_code == 200
    body = competitors.json()
    assert body["category"] == "cooking_oil"
    assert body["category_median_etb"] is not None
    assert body["items"]


def test_oos_endpoint_lists_seeded_alerts(database_client: TestClient) -> None:
    response = database_client.get("/api/analytics/oos", params={"days": 30})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] > 0
    assert body["items"]
    assert body["items"][0]["product_name"]


def test_market_insights_csv_export(database_client: TestClient) -> None:
    response = database_client.get(
        "/api/exports/market-insights.csv",
        params={"level": "district", "category": "cooking_oil"},
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    text = response.text
    assert "product" in text.splitlines()[0]
    assert "mrp_etb" in text
    assert "cooking_oil" in text


def test_pulse_includes_insights_metrics(database_client: TestClient) -> None:
    response = database_client.get("/api/pulse")

    assert response.status_code == 200
    metrics = response.json()["metrics"]
    assert "mrp_compliance_pct" in metrics
    assert "oos_rate_pct" in metrics
    assert "categories_covered" in metrics
    assert "active_oos_alerts" in metrics


async def test_oos_ingest_accepts_without_price(
    writable_session: AsyncSession,
) -> None:
    from app.models.product import Product
    from app.models.store import Store

    product = await writable_session.get(Product, OIL.id)
    store = await writable_session.get(Store, SELAM.id)
    assert product is not None and store is not None

    evidence, decision = await submit_oos_evidence(
        writable_session,
        product=product,
        store_id=store.id,
        source_type=EvidenceSource.STORE_VISIT,
        observed_at=SEED_NOW,
        now=SEED_NOW,
    )
    await writable_session.commit()

    assert evidence.is_oos is True
    assert evidence.price_etb is None
    assert decision.status.value == "accepted"


def test_fixture_mode_insights_routes() -> None:
    from app.main import app

    with TestClient(app) as client:
        assert client.get("/api/analytics/compliance").status_code == 200
        assert client.get("/api/analytics/districts").status_code == 200
        assert client.get("/api/analytics/oos").status_code == 200
        assert client.get("/api/analytics/competitors").status_code == 200
        assert client.get("/api/exports/market-insights.csv").status_code == 200
        pulse = client.get("/api/pulse").json()["metrics"]
        assert pulse["mrp_compliance_pct"] == 24.2
