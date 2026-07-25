"""Turn free text from a receipt, a shelf tag, or a scraper into one product.

The pure half canonicalizes strings and unifies units so that `1000ML`,
`1 l`, and `1L` all collapse to the same token. The database half matches that
canonical text against `product_alias`, first exactly, then by trigram
similarity, and writes every successful match back as a new alias so the same
receipt line never has to be matched twice.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.enums import SizeUnit
from app.models.product import Product, ProductAlias
from app.services.ocr import CatalogCandidate, ExtractionError, choose_catalog_match

# Above this, trigram similarity is trusted on its own; below it, Gemini is asked
# to choose between the closest catalogue entries.
TRIGRAM_THRESHOLD = 0.55
CANDIDATE_LIMIT = 5

MatchMethod = Literal["alias_exact", "trigram", "gemini", "new_product"]

UNIT_ALIASES: dict[str, SizeUnit] = {
    "ml": SizeUnit.MILLILITER,
    "mls": SizeUnit.MILLILITER,
    "milliliter": SizeUnit.MILLILITER,
    "millilitre": SizeUnit.MILLILITER,
    "cc": SizeUnit.MILLILITER,
    "l": SizeUnit.LITER,
    "lt": SizeUnit.LITER,
    "ltr": SizeUnit.LITER,
    "liter": SizeUnit.LITER,
    "litre": SizeUnit.LITER,
    "liters": SizeUnit.LITER,
    "litres": SizeUnit.LITER,
    "g": SizeUnit.GRAM,
    "gr": SizeUnit.GRAM,
    "gm": SizeUnit.GRAM,
    "gms": SizeUnit.GRAM,
    "gram": SizeUnit.GRAM,
    "grams": SizeUnit.GRAM,
    "kg": SizeUnit.KILOGRAM,
    "kgs": SizeUnit.KILOGRAM,
    "kilo": SizeUnit.KILOGRAM,
    "kilos": SizeUnit.KILOGRAM,
    "kilogram": SizeUnit.KILOGRAM,
    "kilograms": SizeUnit.KILOGRAM,
    "pc": SizeUnit.PIECE,
    "pcs": SizeUnit.PIECE,
    "piece": SizeUnit.PIECE,
    "pieces": SizeUnit.PIECE,
}

_ALIAS_PATTERN = "|".join(sorted(UNIT_ALIASES, key=len, reverse=True))
SIZE_TOKEN = re.compile(rf"(\d+(?:[.,]\d+)?)\s*({_ALIAS_PATTERN})(?![a-z0-9])")
_STRAY_DOT = re.compile(r"(?<!\d)\.|\.(?!\d)")
_NOISE = re.compile(r"[^a-z0-9.]+")
_TRIGRAM_WORD = re.compile(r"[a-z0-9.]+")


def unify_size(value: float, unit: SizeUnit) -> tuple[float, SizeUnit]:
    """Express a size in the unit a shopper would read off the pack."""
    if unit is SizeUnit.MILLILITER and value >= 1000:
        return value / 1000, SizeUnit.LITER
    if unit is SizeUnit.LITER and 0 < value < 1:
        return value * 1000, SizeUnit.MILLILITER
    if unit is SizeUnit.GRAM and value >= 1000:
        return value / 1000, SizeUnit.KILOGRAM
    if unit is SizeUnit.KILOGRAM and 0 < value < 1:
        return value * 1000, SizeUnit.GRAM
    return value, unit


def format_number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def size_token(value: float, unit: SizeUnit) -> str:
    """The compact size a canonical string carries: `1l`, `175g`, `2piece`."""
    unified_value, unified_unit = unify_size(value, unit)
    return f"{format_number(unified_value)}{unified_unit.value}"


def _rewrite_size(match: re.Match[str]) -> str:
    value = float(match.group(1).replace(",", "."))
    return f" {size_token(value, UNIT_ALIASES[match.group(2)])} "


def canonicalize(raw: str) -> str:
    """Reduce a raw product string to comparable lowercase text.

    `HAYAT OIL 1000ML` and `Hayat Oil, 1 Litre` both become `hayat oil 1l`,
    which is what makes an exact alias lookup worth trying before anything
    slower.
    """
    text = unicodedata.normalize("NFKC", raw).casefold()
    text = SIZE_TOKEN.sub(_rewrite_size, text)
    text = _NOISE.sub(" ", text)
    text = _STRAY_DOT.sub(" ", text)
    return " ".join(text.split())


def trigrams(value: str) -> set[str]:
    """Pad and split like `pg_trgm` does, so scores match Postgres."""
    grams: set[str] = set()
    for word in _TRIGRAM_WORD.findall(value):
        padded = f"  {word} "
        grams.update(padded[index : index + 3] for index in range(len(padded) - 2))
    return grams


def trigram_similarity(left: str, right: str) -> float:
    """`pg_trgm.similarity` in Python, for SQLite development and tests."""
    left_grams = trigrams(left)
    right_grams = trigrams(right)
    if not left_grams or not right_grams:
        return 0.0
    return len(left_grams & right_grams) / len(left_grams | right_grams)


@dataclass(frozen=True, slots=True)
class Match:
    """What one piece of raw text turned out to be."""

    product: Product | None
    confidence: float
    method: MatchMethod


@dataclass(frozen=True, slots=True)
class Candidate:
    product: Product
    similarity: float


async def match_alias(session: AsyncSession, normalized_text: str) -> Product | None:
    return await session.scalar(
        select(Product)
        .join(ProductAlias, ProductAlias.product_id == Product.id)
        .where(ProductAlias.normalized_text == normalized_text)
    )


async def trigram_candidates(
    session: AsyncSession,
    normalized_text: str,
    *,
    limit: int = CANDIDATE_LIMIT,
) -> list[Candidate]:
    """The closest aliases by trigram similarity, best first."""
    if session.get_bind().dialect.name == "postgresql":
        similarity = func.similarity(ProductAlias.normalized_text, normalized_text)
        rows = await session.execute(
            select(Product, similarity)
            .join(ProductAlias, ProductAlias.product_id == Product.id)
            .order_by(similarity.desc())
            .limit(limit)
        )
        return [Candidate(product=product, similarity=float(score)) for product, score in rows]

    rows = await session.execute(
        select(Product, ProductAlias.normalized_text).join(
            ProductAlias, ProductAlias.product_id == Product.id
        )
    )
    scored = [
        Candidate(product=product, similarity=trigram_similarity(alias, normalized_text))
        for product, alias in rows
    ]
    return sorted(scored, key=lambda candidate: candidate.similarity, reverse=True)[:limit]


async def remember_alias(
    session: AsyncSession,
    product_id: UUID,
    raw_text: str,
    *,
    source: str,
) -> bool:
    """Write a match back so the same wording never needs matching again.

    This is what makes the second identical receipt cost nothing: the exact
    lookup at the top of `resolve_text` hits from then on.
    """
    normalized = canonicalize(raw_text)
    if not normalized:
        return False

    already_known = await session.scalar(
        select(ProductAlias.id).where(ProductAlias.normalized_text == normalized)
    )
    if already_known is not None:
        return False

    session.add(
        ProductAlias(
            product_id=product_id,
            raw_text=raw_text[:300],
            normalized_text=normalized,
            source=source,
        )
    )
    await session.flush()
    return True


async def resolve_text(
    session: AsyncSession,
    raw_text: str,
    *,
    source: str = "receipt",
    allow_gemini: bool = True,
) -> Match:
    """Match raw text to a catalogue product, cheapest method first."""
    normalized = canonicalize(raw_text)
    if not normalized:
        return Match(product=None, confidence=0.0, method="new_product")

    exact = await match_alias(session, normalized)
    if exact is not None:
        return Match(product=exact, confidence=1.0, method="alias_exact")

    candidates = await trigram_candidates(session, normalized)
    best = candidates[0] if candidates else None
    if best is not None and best.similarity >= TRIGRAM_THRESHOLD:
        await remember_alias(session, best.product.id, raw_text, source=source)
        return Match(product=best.product, confidence=best.similarity, method="trigram")

    if not allow_gemini or not get_settings().gemini_api_key or not candidates:
        near_miss = best.similarity if best else 0.0
        return Match(product=None, confidence=near_miss, method="new_product")

    return await _ask_gemini(session, raw_text, candidates, source=source)


async def _ask_gemini(
    session: AsyncSession,
    raw_text: str,
    candidates: list[Candidate],
    *,
    source: str,
) -> Match:
    by_id = {str(candidate.product.id): candidate.product for candidate in candidates}
    try:
        choice = await choose_catalog_match(
            raw_text,
            [
                CatalogCandidate(
                    product_id=str(candidate.product.id),
                    canonical_name=candidate.product.canonical_name,
                    similarity=candidate.similarity,
                )
                for candidate in candidates
            ],
        )
    except ExtractionError:
        # A missing key or a Gemini outage must not lose the receipt line; it
        # simply stays unmatched and the shopper is shown that.
        return Match(product=None, confidence=candidates[0].similarity, method="new_product")

    chosen = by_id.get(choice.product_id or "")
    if choice.match != "existing" or chosen is None:
        return Match(product=None, confidence=choice.confidence, method="new_product")

    await remember_alias(session, chosen.id, raw_text, source=source)
    return Match(product=chosen, confidence=choice.confidence, method="gemini")
