"""Canonicalization, unit unification, and alias matching.

The alias tests run against the seeded catalog on SQLite, so they exercise the
Python trigram measure. It is written to score the same way `pg_trgm` does, which
the padding test pins down.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProductAlias
from app.models.enums import SizeUnit
from app.seed import read_products
from app.services.normalize import (
    TRIGRAM_THRESHOLD,
    canonicalize,
    match_alias,
    remember_alias,
    resolve_text,
    size_token,
    trigram_candidates,
    trigram_similarity,
    trigrams,
    unify_size,
)

PRODUCTS = {product.canonical_name: product for product in read_products()}
OIL = PRODUCTS["Hayat Cooking Oil 1L"]
SUGAR = PRODUCTS["Shega White Sugar 1kg"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Hayat Cooking Oil 1L", "hayat cooking oil 1l"),
        ("HAYAT COOKING OIL 1000ML", "hayat cooking oil 1l"),
        ("Hayat Cooking Oil, 1 Litre", "hayat cooking oil 1l"),
        ("hayat cooking oil 1 lt.", "hayat cooking oil 1l"),
        ("Shega White Sugar 1000g", "shega white sugar 1kg"),
        ("Shega  White   Sugar  1KG", "shega white sugar 1kg"),
        ("Ambo Water 500ML", "ambo water 500ml"),
        ("Ambo Water 0.5L", "ambo water 500ml"),
        ("Pasta 1,5kg", "pasta 1.5kg"),
        ("Lifebuoy Soap (175 gram)", "lifebuoy soap 175g"),
        ("Tea 20 pcs", "tea 20piece"),
        # Fullwidth characters on purpose: some Amharic keyboards produce them.
        ("ＡＭＢＯ　１Ｌ", "ambo 1l"),  # noqa: RUF001
    ],
)
def test_canonicalize_collapses_the_same_product_to_one_string(raw: str, expected: str) -> None:
    assert canonicalize(raw) == expected


def test_canonicalize_of_nothing_is_empty() -> None:
    assert canonicalize("   ") == ""
    assert canonicalize("!!!") == ""


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        (1000, SizeUnit.MILLILITER, (1, SizeUnit.LITER)),
        (1500, SizeUnit.MILLILITER, (1.5, SizeUnit.LITER)),
        (500, SizeUnit.MILLILITER, (500, SizeUnit.MILLILITER)),
        (0.5, SizeUnit.LITER, (500, SizeUnit.MILLILITER)),
        (1000, SizeUnit.GRAM, (1, SizeUnit.KILOGRAM)),
        (175, SizeUnit.GRAM, (175, SizeUnit.GRAM)),
        (0.25, SizeUnit.KILOGRAM, (250, SizeUnit.GRAM)),
        (6, SizeUnit.PIECE, (6, SizeUnit.PIECE)),
    ],
)
def test_unify_size_moves_between_units(
    value: float,
    unit: SizeUnit,
    expected: tuple[float, SizeUnit],
) -> None:
    assert unify_size(value, unit) == expected


def test_size_token_drops_trailing_zeros() -> None:
    assert size_token(1, SizeUnit.LITER) == "1l"
    assert size_token(1.500, SizeUnit.LITER) == "1.5l"
    assert size_token(1000, SizeUnit.GRAM) == "1kg"


def test_trigrams_pad_each_word_the_way_pg_trgm_does() -> None:
    assert trigrams("oil") == {"  o", " oi", "oil", "il "}


def test_trigram_similarity_is_one_for_identical_text_and_zero_for_nothing_shared() -> None:
    assert trigram_similarity("hayat oil 1l", "hayat oil 1l") == 1.0
    assert trigram_similarity("hayat oil", "zzz qqq") == 0.0
    assert trigram_similarity("", "hayat oil") == 0.0


def test_trigram_similarity_ranks_the_closer_wording_higher() -> None:
    target = canonicalize("Hayat Cooking Oil 1L")
    close = trigram_similarity(canonicalize("HAYAT OIL 1L"), target)
    far = trigram_similarity(canonicalize("Shega White Sugar 1kg"), target)

    assert close >= TRIGRAM_THRESHOLD > far


@pytest.mark.asyncio
async def test_the_seed_leaves_an_alias_for_every_product(session: AsyncSession) -> None:
    for product in PRODUCTS.values():
        found = await match_alias(session, canonicalize(product.canonical_name))
        assert found is not None and found.id == product.id


@pytest.mark.asyncio
async def test_trigram_candidates_come_back_best_first(session: AsyncSession) -> None:
    candidates = await trigram_candidates(session, canonicalize("HAYAT OIL 1L"), limit=3)

    assert candidates[0].product.id == OIL.id
    assert candidates == sorted(candidates, key=lambda item: item.similarity, reverse=True)
    assert len(candidates) == 3


@pytest.mark.asyncio
async def test_unrelated_text_matches_nothing(session: AsyncSession) -> None:
    match = await resolve_text(session, "Zambezi Floor Polish 4L", allow_gemini=False)

    assert match.product is None
    assert match.method == "new_product"
    assert match.confidence < TRIGRAM_THRESHOLD


@pytest.mark.asyncio
async def test_remember_alias_writes_once_and_never_steals(
    writable_session: AsyncSession,
) -> None:
    assert await remember_alias(writable_session, OIL.id, "HAYAT OIL 1L", source="receipt") is True
    assert await remember_alias(writable_session, OIL.id, "HAYAT OIL 1L", source="receipt") is False
    # The same wording cannot be claimed by a second product.
    assert (
        await remember_alias(writable_session, SUGAR.id, "hayat oil 1l", source="receipt") is False
    )

    owners = list(
        await writable_session.scalars(
            select(ProductAlias.product_id).where(ProductAlias.normalized_text == "hayat oil 1l")
        )
    )
    assert owners == [OIL.id]


@pytest.mark.asyncio
async def test_remember_alias_ignores_unusable_text(writable_session: AsyncSession) -> None:
    assert await remember_alias(writable_session, OIL.id, "***", source="receipt") is False
