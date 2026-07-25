"""Gemini reads receipts, shelf tags, and product photos.

Every call pins `temperature=0.1` and hands Gemini a JSON schema it must fill,
so the output is a model instance rather than prose to parse. Amharic receipts
are the accuracy risk the design accepts: the app shows every extraction for the
shopper to correct before it becomes evidence.

The SDK is imported inside these functions on purpose: a fixture-mode deployment
serves the whole contract without ever reading an image, and it should not pay the
SDK's import cost at boot to do it.
"""

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from app.config import get_settings

TEMPERATURE = 0.1
MAX_CANDIDATES = 5

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
) -> Answer:
    client = _client()
    from google.genai import types

    parts: list[Any] = [prompt]
    if image is not None:
        parts.insert(0, types.Part.from_bytes(data=image, mime_type=mime_type))

    try:
        response = await client.aio.models.generate_content(
            model=get_settings().gemini_model,
            contents=parts,
            config=types.GenerateContentConfig(
                temperature=TEMPERATURE,
                response_mime_type="application/json",
                response_schema=answer,
            ),
        )
    except Exception as error:  # the SDK raises its own hierarchy
        raise ExtractionError(f"Gemini call failed: {error}") from error

    if not response.text:
        raise ExtractionError("Gemini returned an empty response")
    try:
        return answer.model_validate_json(response.text)
    except ValueError as error:
        raise ExtractionError(f"Gemini returned unusable JSON: {error}") from error


async def extract_receipt(image: bytes, mime_type: str = "image/jpeg") -> ReceiptDocument:
    return await _ask(ReceiptDocument, RECEIPT_PROMPT, image=image, mime_type=mime_type)


async def extract_shelf_tag(image: bytes, mime_type: str = "image/jpeg") -> ShelfTag:
    return await _ask(ShelfTag, SHELF_PROMPT, image=image, mime_type=mime_type)


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
