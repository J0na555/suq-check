"""The read endpoints against a seeded database rather than fixtures.

These are the same routes `test_contract.py` checks in fixture mode, so between
the two files every response shape is exercised both ways.
"""

from fastapi.testclient import TestClient

from app.seed import read_products, read_stores
from app.seed.catalog import Coverage, product_id, store_id

PRODUCTS = {product.canonical_name: product for product in read_products()}
STORES = {store.name: store for store in read_stores()}

OIL = PRODUCTS["Hayat Cooking Oil 1L"]
SOAP = PRODUCTS["Lifebuoy Soap 175g"]
STALE = PRODUCTS["Omo Detergent Powder 1kg"]
SELAM_MART = STORES["Selam Mart"]

MISSING_PRODUCT = product_id("Nobody", "Imaginary Cola 2L", 2, OIL.size_unit)
MISSING_STORE = store_id("Imaginary Mart", "Nowhere")


def test_catalog_csvs_hold_the_full_confidence_spread() -> None:
    coverages = {product.coverage for product in PRODUCTS.values()}

    assert coverages == set(Coverage)


def test_search_returns_priced_products_with_a_band(database_client: TestClient) -> None:
    response = database_client.get("/api/products", params={"q": "hayat"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == str(OIL.id)
    assert item["size_label"] == "1 L"
    assert item["market_price_etb"] > 0
    assert item["confidence_band"] == "high"
    assert item["thumbnail_url"] is None


def test_search_falls_back_to_fuzzy_matching_on_a_typo(database_client: TestClient) -> None:
    response = database_client.get("/api/products", params={"q": "hayatt cookng oil"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [str(OIL.id)]


def test_category_filter_and_pagination(database_client: TestClient) -> None:
    response = database_client.get("/api/products", params={"category": "soap"})

    assert response.status_code == 200
    body = response.json()
    soap_ids = {str(product.id) for product in PRODUCTS.values() if product.category.value == "soap"}
    assert {item["id"] for item in body["items"]} == soap_ids
    assert str(SOAP.id) in soap_ids

    paged = database_client.get("/api/products", params={"limit": 2, "offset": 1})
    assert paged.status_code == 200
    assert len(paged.json()["items"]) == 2
    assert paged.json()["total"] == len(PRODUCTS)


def test_product_detail_explains_a_stored_score(database_client: TestClient) -> None:
    response = database_client.get(f"/api/products/{OIL.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["barcode"] == OIL.barcode
    assert body["confidence"] >= 85
    assert body["confidence_breakdown"]["score"] == body["confidence"]
    assert [factor["name"] for factor in body["confidence_breakdown"]["factors"]] == [
        "volume",
        "agreement",
        "freshness",
        "diversity",
    ]
    low, high = body["price_range_etb"]
    assert low <= body["market_price_etb"] <= high
    assert body["sources"]
    assert {source["source_type"] for source in body["sources"]} <= {
        "partner",
        "receipt",
        "scrape",
        "store_visit",
        "shelf_photo",
        "community",
    }
    assert len(body["history"]) > 30
    assert body["updated_at"].endswith("Z")


def test_stale_product_reports_a_capped_score(database_client: TestClient) -> None:
    response = database_client.get(f"/api/products/{STALE.id}")

    assert response.status_code == 200
    breakdown = response.json()["confidence_breakdown"]
    assert breakdown["capped"] is True
    assert "capped at 60" in breakdown["cap_reason"]
    assert response.json()["confidence"] == 60


def test_every_seeded_product_has_a_detail_page(database_client: TestClient) -> None:
    for product in PRODUCTS.values():
        assert database_client.get(f"/api/products/{product.id}").status_code == 200


def test_unknown_product_is_404(database_client: TestClient) -> None:
    response = database_client.get(f"/api/products/{MISSING_PRODUCT}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_nearby_stores_measure_distance_and_judge_the_price(
    database_client: TestClient,
) -> None:
    response = database_client.get(
        f"/api/products/{OIL.id}/stores",
        params={
            "latitude": SELAM_MART.latitude,
            "longitude": SELAM_MART.longitude,
            "radius_m": 50_000,
        },
    )

    assert response.status_code == 200
    body = response.json()
    market = body["market_price_etb"]
    items = body["items"]
    assert items
    assert [item["distance_m"] for item in items] == sorted(
        item["distance_m"] for item in items
    )
    nearest = items[0]
    assert nearest["id"] == str(SELAM_MART.id)
    assert nearest["distance_m"] == 0
    for item in items:
        assert item["difference_from_market_etb"] == round(item["price_etb"] - market, 2)
        expected = (
            "cheap"
            if item["price_etb"] < market * 0.99
            else "high"
            if item["price_etb"] > market * 1.01
            else "fair"
        )
        assert item["verdict"] == expected


def test_a_tight_radius_excludes_distant_stores(database_client: TestClient) -> None:
    wide = database_client.get(
        f"/api/products/{OIL.id}/stores",
        params={
            "latitude": SELAM_MART.latitude,
            "longitude": SELAM_MART.longitude,
            "radius_m": 50_000,
        },
    ).json()
    tight = database_client.get(
        f"/api/products/{OIL.id}/stores",
        params={
            "latitude": SELAM_MART.latitude,
            "longitude": SELAM_MART.longitude,
            "radius_m": 1_000,
        },
    ).json()

    assert len(tight["items"]) < len(wide["items"])
    assert all(item["distance_m"] <= 1_000 for item in tight["items"])


def test_nearby_stores_without_a_location_omit_distance(database_client: TestClient) -> None:
    response = database_client.get(f"/api/products/{OIL.id}/stores")

    assert response.status_code == 200
    items = response.json()["items"]
    assert all(item["distance_m"] is None for item in items)
    assert [item["price_etb"] for item in items] == sorted(
        item["price_etb"] for item in items
    )


def test_store_detail_indexes_against_the_market(database_client: TestClient) -> None:
    response = database_client.get(f"/api/stores/{SELAM_MART.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == SELAM_MART.name
    assert body["district"] == SELAM_MART.district
    assert body["product_count"] > 0
    assert 80 < body["average_price_index"] < 120
    assert body["last_reported_at"].endswith("Z")


def test_unknown_store_is_404(database_client: TestClient) -> None:
    response = database_client.get(f"/api/stores/{MISSING_STORE}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Store not found"


def test_pulse_counts_the_market_it_can_see(database_client: TestClient) -> None:
    response = database_client.get("/api/pulse")

    assert response.status_code == 200
    body = response.json()
    metrics = body["metrics"]
    assert metrics["products_covered"] == len(PRODUCTS)
    assert metrics["stores_reporting"] > 0
    assert metrics["verified_prices_today"] > 0
    assert 0 < metrics["average_confidence"] <= 100
    kinds = [mover["kind"] for mover in body["movers"]]
    assert "most_verified" in kinds
    assert len(kinds) == len(set(kinds))
    assert body["cheapest_district"] in {store.district for store in STORES.values()}
    assert body["most_active_store"] in STORES


def test_pulse_movers_show_the_seeded_trends(database_client: TestClient) -> None:
    movers = {mover["kind"]: mover for mover in database_client.get("/api/pulse").json()["movers"]}

    assert movers["fastest_rising"]["value"] > 0
    assert movers["fastest_rising"]["display_value"].startswith("+")
    assert movers["largest_drop"]["value"] < 0
    assert movers["most_verified"]["display_value"].endswith("% confidence")


def test_trends_read_the_history_table(database_client: TestClient) -> None:
    response = database_client.get("/api/analytics/trends", params={"period_days": 60})

    assert response.status_code == 200
    body = response.json()
    assert body["period_days"] == 60
    assert body["items"]

    # Top movers are capped; with several oils drifting together the list is oil-
    # heavy, so assert the seeded directions rather than exact SKU membership.
    assert any(item["direction"] == "up" for item in body["items"])
    assert any(item["direction"] == "down" for item in body["items"])
    oils = [
        item
        for item in body["items"]
        if any(token in item["product_name"] for token in ("Oil", "oil"))
    ]
    sugars = [item for item in body["items"] if "Sugar" in item["product_name"]]
    assert oils and all(item["direction"] == "up" for item in oils)
    assert all(item["direction"] == "down" for item in sugars)
    for item in body["items"]:
        assert len(item["points"]) >= 2
        assert item["points"][0]["day"] < item["points"][-1]["day"]


def test_evidence_log_shows_real_gate_decisions(database_client: TestClient) -> None:
    response = database_client.get("/api/evidence", params={"limit": 100})

    assert response.status_code == 200
    body = response.json()
    statuses = {item["status"] for item in body["items"]}
    assert {"accepted", "pending"} <= statuses

    pending = database_client.get("/api/evidence", params={"status": "pending"}).json()
    assert pending["total"] >= 1
    assert all(item["status"] == "pending" for item in pending["items"])
    assert all("verification" in item["rejection_reason"] for item in pending["items"])

    rejected = database_client.get("/api/evidence", params={"status": "rejected"}).json()
    assert rejected["total"] >= 1
    assert all(item["rejection_reason"] for item in rejected["items"])
