"""How the Gemini calls are shaped, and what happens when they go wrong.

No test here reaches the network: a stub stands in for the SDK client so the
request we build and the answers we accept are both pinned down.
"""

import json
from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest

from app.services import ocr
from app.services.ocr import (
    CatalogCandidate,
    CatalogChoice,
    ExtractionError,
    IdentifiedProduct,
    MediaResolution,
    PriceListDocument,
    ReceiptDocument,
    ShelfTag,
)

IMAGE = b"\xff\xd8\xff\xdb pretend this is a receipt"

RECEIPT_JSON = json.dumps(
    {
        "store_name": "Selam Mart",
        "observed_on": "2026-07-20",
        "total_etb": 545.0,
        "ocr_confidence": 0.88,
        "items": [
            {
                "raw_text": "HAYAT COOKING OIL 1L",
                "quantity": 1,
                "unit_price_etb": 340.0,
                "total_price_etb": 340.0,
            }
        ],
    }
)

SHELF_JSON = json.dumps({"raw_product_text": "Ambo 1L", "price_etb": 32, "ocr_confidence": 0.9})

PRICE_LIST_JSON = json.dumps(
    {
        "store_name": "Selam Mart",
        "observed_on": "2026-07-20",
        "ocr_confidence": 0.91,
        "items": [
            {"raw_text": "TENA COOKING OIL 1L", "price_etb": 355.0},
            {"raw_text": "CHEF LUCA SPAGHETTI 500G", "price_etb": 95.0},
            {"raw_text": "አስትኮ ዱቄት 1ኪ.ግ", "price_etb": 95.0},
        ],
    }
)


class FakeCall:
    """Records one generate_content call and replies with canned text."""

    def __init__(self, text: str | None) -> None:
        self.text = text
        self.kwargs: dict[str, Any] = {}
        self.error: Exception | None = None
        self.usage_metadata = SimpleNamespace(
            prompt_token_count=120,
            candidates_token_count=40,
            total_token_count=160,
        )

    async def generate_content(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        if self.error is not None:
            raise self.error
        return SimpleNamespace(text=self.text, usage_metadata=self.usage_metadata)


@pytest.fixture
def gemini(monkeypatch: pytest.MonkeyPatch):
    """Installs a stub client and hands the test the call it captured."""

    def install(text: str | None = "{}", *, error: Exception | None = None) -> FakeCall:
        call = FakeCall(text)
        call.error = error
        client = SimpleNamespace(aio=SimpleNamespace(models=call))
        monkeypatch.setattr(ocr, "_client", lambda: client)
        return call

    return install


@pytest.mark.asyncio
async def test_a_receipt_call_sends_the_image_before_the_prompt(gemini) -> None:
    call = gemini(RECEIPT_JSON)

    receipt = await ocr.extract_receipt(IMAGE, "image/png")

    image_part, prompt = call.kwargs["contents"]
    assert image_part.inline_data.data == IMAGE
    assert image_part.inline_data.mime_type == "image/png"
    assert prompt == ocr.RECEIPT_PROMPT
    assert call.kwargs["config"].media_resolution.value == MediaResolution.MEDIUM
    assert receipt.store_name == "Selam Mart"
    assert receipt.observed_date == date(2026, 7, 20)
    assert receipt.items[0].unit_price_etb == 340.0


@pytest.mark.asyncio
async def test_usage_metadata_is_available_via_pop_usage(gemini) -> None:
    gemini(RECEIPT_JSON)

    await ocr.extract_receipt(IMAGE)
    usage = ocr.pop_usage()

    assert usage is not None
    assert usage.model == ocr.get_settings().gemini_model
    assert usage.prompt_token_count == 120
    assert usage.candidates_token_count == 40
    assert usage.total_token_count == 160
    assert ocr.pop_usage() is None
    assert usage.as_payload(shared_across_observations=4)["shared_across_observations"] == 4


@pytest.mark.asyncio
async def test_a_price_list_call_uses_high_resolution_and_the_directive_prompt(
    gemini,
) -> None:
    call = gemini(PRICE_LIST_JSON)

    document = await ocr.extract_price_list(IMAGE, "image/png")

    image_part, prompt = call.kwargs["contents"]
    assert image_part.inline_data.data == IMAGE
    assert prompt == ocr.PRICE_LIST_PROMPT
    assert "Directive 159/2024" in prompt
    assert "Amharic" in prompt
    config = call.kwargs["config"]
    assert config.media_resolution.value == MediaResolution.HIGH
    assert config.response_schema is PriceListDocument
    assert document.store_name == "Selam Mart"
    assert document.observed_date == date(2026, 7, 20)
    assert len(document.items) == 3
    assert document.items[0].price_etb == 355.0


@pytest.mark.asyncio
async def test_every_call_pins_the_temperature_the_schema_and_the_configured_model(
    gemini,
) -> None:
    call = gemini(SHELF_JSON)

    await ocr.extract_shelf_tag(IMAGE)

    config = call.kwargs["config"]
    assert config.temperature == ocr.TEMPERATURE
    assert config.response_mime_type == "application/json"
    assert config.response_schema is ShelfTag
    assert config.media_resolution is None
    assert call.kwargs["model"] == ocr.get_settings().gemini_model


@pytest.mark.asyncio
async def test_identifying_a_product_returns_the_pack_as_gemini_read_it(gemini) -> None:
    gemini(
        json.dumps(
            {
                "canonical_name": "Hayat Cooking Oil 1L",
                "brand": "Hayat",
                "category": "cooking_oil",
                "size_value": 1,
                "size_unit": "l",
                "confidence": 0.81,
            }
        )
    )

    seen = await ocr.identify_product(IMAGE)

    assert seen == IdentifiedProduct(
        canonical_name="Hayat Cooking Oil 1L",
        brand="Hayat",
        category="cooking_oil",
        size_value=1,
        size_unit="l",
        confidence=0.81,
    )


@pytest.mark.asyncio
async def test_a_matching_call_carries_the_candidates_and_no_image(gemini) -> None:
    call = gemini(json.dumps({"match": "existing", "product_id": "abc", "confidence": 0.9}))
    candidates = [
        CatalogCandidate(product_id=f"id-{index}", canonical_name=f"Oil {index}", similarity=0.5)
        for index in range(ocr.MAX_CANDIDATES + 3)
    ]

    choice = await ocr.choose_catalog_match("HAYAT OIL 1L", candidates)

    (prompt,) = call.kwargs["contents"]
    assert "HAYAT OIL 1L" in prompt
    assert "id-0: Oil 0 (similarity 0.50)" in prompt
    # The prompt stays short: only the closest few are worth asking about.
    assert f"id-{ocr.MAX_CANDIDATES}" not in prompt
    assert choice == CatalogChoice(match="existing", product_id="abc", confidence=0.9)


@pytest.mark.asyncio
async def test_no_candidates_still_produces_a_usable_prompt(gemini) -> None:
    call = gemini(json.dumps({"match": "new", "confidence": 0.2}))

    choice = await ocr.choose_catalog_match("Zambezi Floor Polish 4L", [])

    assert "- none" in call.kwargs["contents"][0]
    assert choice.product_id is None


@pytest.mark.asyncio
async def test_an_unparsable_receipt_date_is_dropped_rather_than_guessed(gemini) -> None:
    gemini(json.dumps({"observed_on": "20/07/2026", "ocr_confidence": 0.5, "items": []}))

    receipt = await ocr.extract_receipt(IMAGE)

    assert receipt.observed_date is None


def test_a_receipt_with_no_date_has_no_date() -> None:
    assert ReceiptDocument(ocr_confidence=0.5).observed_date is None


@pytest.mark.asyncio
async def test_a_transport_failure_is_reported_as_an_extraction_failure(gemini) -> None:
    gemini(error=RuntimeError("503 Service Unavailable"))

    with pytest.raises(ExtractionError, match="503 Service Unavailable"):
        await ocr.extract_receipt(IMAGE)


@pytest.mark.asyncio
async def test_an_empty_answer_is_an_extraction_failure(gemini) -> None:
    gemini(None)

    with pytest.raises(ExtractionError, match="empty response"):
        await ocr.extract_shelf_tag(IMAGE)


@pytest.mark.asyncio
async def test_an_answer_that_breaks_the_schema_is_an_extraction_failure(gemini) -> None:
    # A shelf tag cannot cost nothing, and the schema says so.
    gemini(json.dumps({"raw_product_text": "Ambo 1L", "price_etb": 0, "ocr_confidence": 0.9}))

    with pytest.raises(ExtractionError, match="unusable JSON"):
        await ocr.extract_shelf_tag(IMAGE)


@pytest.mark.asyncio
async def test_without_a_key_nothing_is_sent_at_all(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ocr,
        "get_settings",
        lambda: SimpleNamespace(gemini_api_key="", gemini_model="gemini-2.5-flash"),
    )
    ocr._client.cache_clear()

    with pytest.raises(ExtractionError, match="GEMINI_API_KEY is not set"):
        await ocr.extract_receipt(IMAGE)

    ocr._client.cache_clear()
