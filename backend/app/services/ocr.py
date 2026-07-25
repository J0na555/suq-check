"""Gemini reads receipts, shelf tags, price lists, and product photos.

Every call pins `temperature=0.1` and hands Gemini a JSON schema it must fill,
so the output is a model instance rather than prose to parse. Amharic receipts
are the accuracy risk the design accepts: the app shows every extraction for the
shopper to correct before it becomes evidence.

Token counts from each call land in a contextvar via `pop_usage()` so ingest can
write them onto evidence without changing every extract return type. Callers that
care about cost must pop immediately after the extract they own — later Gemini
calls (catalog matching) overwrite the same slot.

The SDK is imported inside these functions on purpose: a fixture-mode deployment
serves the whole contract without ever reading an image, and it should not pay the
SDK's import cost at boot to do it.
"""

from contextvars import ContextVar
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from app.config import get_settings

TEMPERATURE = 0.1
MAX_CANDIDATES = 5

_last_usage: ContextVar["GeminiUsage | None"] = ContextVar("gemini_usage", default=None)


class MediaResolution(StrEnum):
    """Token budget for image inputs. High costs roughly 7x medium."""

    MEDIUM = "MEDIA_RESOLUTION_MEDIUM"
    HIGH = "MEDIA_RESOLUTION_HIGH"


RECEIPT_PROMPT = """
You are reading a supermarket or shop receipt from Addis Ababa, Ethiopia.
Prices are Ethiopian birr. The receipt may be in English, Amharic, or both.

Return every purchased line item exactly as printed in `raw_text`, including
brand and pack size when they appear. Ignore subtotals, VAT lines, discounts,
loyalty points, and change. If a line shows a quantity, report the single-unit
price in `unit_price_etb` and the line total in `total_price_etb`.

Set `ocr_confidence` to how legible the image was, from 0 to 1.
Leave a field null rather than guessing it.
""".strip()

SHELF_PROMPT = """
You are reading one shelf price tag from a shop in Addis Ababa, Ethiopia.
The price is in Ethiopian birr and may be written in Amharic numerals.

Copy the product description exactly as printed into `raw_product_text` and
report the shelf price in `price_etb`. If the tag shows both a unit price and a
pack price, report the pack price. Set `ocr_confidence` from 0 to 1.
""".strip()

PRICE_LIST_PROMPT = """
You are reading a shop's legally posted retail price list from Addis Ababa,
Ethiopia, as required under Trade Competition and Consumer Protection Authority
Directive 159/2024. The list is typically a paper sheet or board near the
entrance or till. Text may be in Amharic, English, or both; prices are
Ethiopian birr and may use Amharic numerals.

Return every priced product line you can read — typically around 25 items on a
full list. Copy each product description exactly as printed into `raw_text`,
including brand and pack size when shown. Put the posted unit price in
`price_etb`. Ignore headers, footers, store stamps, dates used only as
decoration, and any line without a readable price.

Set `ocr_confidence` to how legible the whole list was, from 0 to 1.
Leave a field null rather than guessing it.
""".strip()

IDENTIFY_PROMPT = """
You are looking at a photo of a packaged household product sold in Ethiopia:
cooking oil, sugar, rice, flour, salt, pasta, coffee, tea, milk, soap,
detergent, toothpaste, shampoo, or bottled water.

Report the brand, the product name as it would be written in a catalogue, and
the pack size. `size_unit` must be one of ml, l, g, kg, piece. `category` must be
one of the fourteen listed above, lowercase with underscores.
""".strip()

MATCH_PROMPT = """
A receipt line has to be matched against a product catalogue.

You are given the raw line and the closest catalogue entries. Answer `existing`
with the `product_id` of the entry that is the same product in the same pack
size, or `new` when none of them is. A different size is a different product.
""".strip()


class ExtractionError(RuntimeError):
    """Gemini could not be reached, or answered with something unusable."""


class ReceiptLine(BaseModel):
    raw_text: str
    quantity: float = Field(default=1, gt=0)
    unit_price_etb: float = Field(gt=0)
    total_price_etb: float = Field(gt=0)


class ReceiptDocument(BaseModel):
    store_name: str | None = None
    observed_on: str | None = Field(default=None, description="ISO date printed on the receipt.")
    total_etb: float | None = None
    ocr_confidence: float = Field(ge=0, le=1)
    items: list[ReceiptLine] = Field(default_factory=list)

    @property
    def observed_date(self) -> date | None:
        if not self.observed_on:
            return None
        try:
            return date.fromisoformat(self.observed_on[:10])
        except ValueError:
            return None


class ShelfTag(BaseModel):
    raw_product_text: str
    price_etb: float = Field(gt=0)
    ocr_confidence: float = Field(ge=0, le=1)


class PriceListLine(BaseModel):
    raw_text: str
    price_etb: float = Field(gt=0)


class PriceListDocument(BaseModel):
    store_name: str | None = None
    observed_on: str | None = Field(
        default=None,
        description="ISO date printed on the price list, if any.",
    )
    ocr_confidence: float = Field(ge=0, le=1)
    items: list[PriceListLine] = Field(default_factory=list)

    @property
    def observed_date(self) -> date | None:
        if not self.observed_on:
            return None
        try:
            return date.fromisoformat(self.observed_on[:10])
        except ValueError:
            return None


class IdentifiedProduct(BaseModel):
    canonical_name: str
    brand: str
    category: str
    size_value: float = Field(gt=0)
    size_unit: str
    confidence: float = Field(ge=0, le=1)


class CatalogChoice(BaseModel):
    match: str = Field(description="`existing` or `new`.")
    product_id: str | None = None
    confidence: float = Field(ge=0, le=1)


@dataclass(frozen=True, slots=True)
class CatalogCandidate:
    product_id: str
    canonical_name: str
    similarity: float


@dataclass(frozen=True, slots=True)
class GeminiUsage:
    """Token counts from one `generate_content` call."""

    model: str
    prompt_token_count: int = 0
    candidates_token_count: int = 0
    total_token_count: int = 0

    def as_payload(self, *, shared_across_observations: int = 1) -> dict[str, Any]:
        """Shape stored on `evidence.raw_payload["gemini"]`.

        Multi-line receipts and price lists share one call across N evidence rows.
        Aggregators divide by `shared_across_observations` so a 28-line list is not
        billed 28 times.
        """
        return {
            "model": self.model,
            "prompt_token_count": self.prompt_token_count,
            "candidates_token_count": self.candidates_token_count,
            "total_token_count": self.total_token_count,
            "shared_across_observations": max(shared_across_observations, 1),
        }


def pop_usage() -> GeminiUsage | None:
    """Take the usage recorded by the most recent `_ask` in this task."""
    usage = _last_usage.get()
    _last_usage.set(None)
    return usage


def remember_usage(usage: GeminiUsage | None) -> None:
    """Test seam: plant usage the way `_ask` would after a real Gemini call."""
    _last_usage.set(usage)


def _usage_from(response: Any, *, model: str) -> GeminiUsage | None:
    metadata = getattr(response, "usage_metadata", None)
    if metadata is None:
        return None
    return GeminiUsage(
        model=model,
        prompt_token_count=int(getattr(metadata, "prompt_token_count", 0) or 0),
        candidates_token_count=int(getattr(metadata, "candidates_token_count", 0) or 0),
        total_token_count=int(getattr(metadata, "total_token_count", 0) or 0),
    )


@lru_cache
def _client() -> Any:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ExtractionError("GEMINI_API_KEY is not set, so images cannot be read")

    try:
        from google import genai
    except ModuleNotFoundError as error:  # pragma: no cover - deployment dependency
        raise ExtractionError("google-genai is not installed") from error

    return genai.Client(api_key=settings.gemini_api_key)


async def _ask[Answer: BaseModel](
    answer: type[Answer],
    prompt: str,
    *,
    image: bytes | None = None,
    mime_type: str = "image/jpeg",
    media_resolution: MediaResolution | None = None,
) -> Answer:
    client = _client()
    from google.genai import types

    parts: list[Any] = [prompt]
    if image is not None:
        parts.insert(0, types.Part.from_bytes(data=image, mime_type=mime_type))

    config_kwargs: dict[str, Any] = {
        "temperature": TEMPERATURE,
        "response_mime_type": "application/json",
        "response_schema": answer,
    }
    if media_resolution is not None:
        config_kwargs["media_resolution"] = types.MediaResolution(media_resolution.value)

    model = get_settings().gemini_model
    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=parts,
            config=types.GenerateContentConfig(**config_kwargs),
        )
    except Exception as error:  # the SDK raises its own hierarchy
        raise ExtractionError(f"Gemini call failed: {error}") from error

    _last_usage.set(_usage_from(response, model=model))

    if not response.text:
        raise ExtractionError("Gemini returned an empty response")
    try:
        return answer.model_validate_json(response.text)
    except ValueError as error:
        raise ExtractionError(f"Gemini returned unusable JSON: {error}") from error


async def extract_receipt(image: bytes, mime_type: str = "image/jpeg") -> ReceiptDocument:
    return await _ask(
        ReceiptDocument,
        RECEIPT_PROMPT,
        image=image,
        mime_type=mime_type,
        media_resolution=MediaResolution.MEDIUM,
    )


async def extract_shelf_tag(image: bytes, mime_type: str = "image/jpeg") -> ShelfTag:
    return await _ask(ShelfTag, SHELF_PROMPT, image=image, mime_type=mime_type)


async def extract_price_list(image: bytes, mime_type: str = "image/jpeg") -> PriceListDocument:
    return await _ask(
        PriceListDocument,
        PRICE_LIST_PROMPT,
        image=image,
        mime_type=mime_type,
        media_resolution=MediaResolution.HIGH,
    )


async def identify_product(image: bytes, mime_type: str = "image/jpeg") -> IdentifiedProduct:
    return await _ask(IdentifiedProduct, IDENTIFY_PROMPT, image=image, mime_type=mime_type)


async def choose_catalog_match(
    raw_text: str,
    candidates: list[CatalogCandidate],
) -> CatalogChoice:
    """Last resort in normalization, once trigram similarity is inconclusive."""
    listing = "\n".join(
        f"- {candidate.product_id}: {candidate.canonical_name} "
        f"(similarity {candidate.similarity:.2f})"
        for candidate in candidates[:MAX_CANDIDATES]
    )
    prompt = f"{MATCH_PROMPT}\n\nReceipt line: {raw_text}\n\nCatalogue:\n{listing or '- none'}"
    return await _ask(CatalogChoice, prompt)
