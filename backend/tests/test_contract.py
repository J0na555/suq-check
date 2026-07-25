from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

OIL_ID = UUID("11111111-1111-4111-8111-111111111111")
SOAP_ID = UUID("33333333-3333-4333-8333-333333333333")
STORE_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


def test_health() -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["fixtures"] is True


def test_product_search_filters_fixture() -> None:
    response = client.get("/api/products", params={"q": "hayat"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == str(OIL_ID)


def test_product_category_filters_fixture() -> None:
    response = client.get("/api/products", params={"category": "soap"})

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == str(SOAP_ID)


def test_high_confidence_product_explains_score() -> None:
    response = client.get(f"/api/products/{OIL_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["confidence"] == 98
    assert len(body["confidence_breakdown"]["factors"]) == 4
    assert body["updated_at"].endswith("Z")


def test_low_confidence_product_is_available_for_demo() -> None:
    response = client.get(f"/api/products/{SOAP_ID}")

    assert response.status_code == 200
    assert response.json()["confidence_band"] == "low"


def test_unknown_product_is_404() -> None:
    response = client.get("/api/products/44444444-4444-4444-8444-444444444444")

    assert response.status_code == 404


def test_nearby_stores_respect_radius() -> None:
    response = client.get(f"/api/products/{OIL_ID}/stores", params={"radius_m": 500})

    assert response.status_code == 200
    assert [item["name"] for item in response.json()["items"]] == ["Selam Mart"]


def test_store_detail() -> None:
    response = client.get(f"/api/stores/{STORE_ID}")

    assert response.status_code == 200
    assert response.json()["average_price_index"] < 100


def test_receipt_upload_contract() -> None:
    response = client.post(
        "/api/evidence/receipt",
        files={"image": ("receipt.jpg", b"fixture-image", "image/jpeg")},
        headers={"X-Device-Id": "test-device"},
    )

    assert response.status_code == 200
    assert len(response.json()["decisions"]) == 2


def test_shelf_upload_contract() -> None:
    response = client.post(
        "/api/evidence/shelf",
        files={"image": ("shelf.jpg", b"fixture-image", "image/jpeg")},
    )

    assert response.status_code == 200
    assert response.json()["decision"]["status"] == "accepted"


def test_manual_evidence_demonstrates_pending_outlier() -> None:
    response = client.post(
        "/api/evidence/manual",
        json={
            "product_id": str(OIL_ID),
            "store_id": str(STORE_ID),
            "price_etb": 120,
            "observed_at": "2026-07-25T12:00:00Z",
            "source_type": "community",
        },
        headers={"X-Device-Id": "test-device"},
    )

    assert response.status_code == 200
    assert response.json()["decision"]["status"] == "pending"


def test_scan_identification_contract() -> None:
    response = client.post(
        "/api/scan/identify",
        files={"image": ("product.jpg", b"fixture-image", "image/jpeg")},
    )

    assert response.status_code == 200
    assert response.json()["product_id"] == str(OIL_ID)


def test_trends_contract() -> None:
    response = client.get("/api/analytics/trends", params={"period_days": 30})

    assert response.status_code == 200
    assert response.json()["period_days"] == 30


def test_evidence_log_lists_every_gate_decision() -> None:
    response = client.get("/api/evidence")

    assert response.status_code == 200
    statuses = {item["status"] for item in response.json()["items"]}
    assert statuses == {"accepted", "pending", "rejected"}


def test_evidence_log_filters_by_status() -> None:
    response = client.get("/api/evidence", params={"status": "pending", "limit": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["items"][0]["price_etb"] == 120
    assert "needs verification" in body["items"][0]["rejection_reason"]


def test_openapi_exposes_exactly_eleven_product_endpoints_plus_health() -> None:
    paths = app.openapi()["paths"]

    operation_count = sum(len(operations) for operations in paths.values())
    assert operation_count == 12
    assert "/healthz" in paths

