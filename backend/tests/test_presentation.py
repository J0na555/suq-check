"""Labels, verdicts, distance, and the fixture switch itself."""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.enums import EvidenceSource, SizeUnit
from app.models.store import Store
from app.repositories.mappers import (
    as_utc,
    distance_expression,
    size_label,
    source_label,
    verdict_for,
)
from app.seed import read_stores

STORES = {store.name: store for store in read_stores()}
SELAM_MART = STORES["Selam Mart"]
CENTRAL = STORES["Central Supermarket"]


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        (Decimal("1"), SizeUnit.LITER, "1 L"),
        (Decimal("1.500"), SizeUnit.LITER, "1.5 L"),
        (Decimal("175"), SizeUnit.GRAM, "175 g"),
        (Decimal("1"), SizeUnit.KILOGRAM, "1 kg"),
        (Decimal("500"), SizeUnit.MILLILITER, "500 ml"),
        (Decimal("6"), SizeUnit.PIECE, "6 piece"),
    ],
)
def test_size_label_reads_like_the_pack(value: Decimal, unit: SizeUnit, expected: str) -> None:
    assert size_label(value, unit) == expected


def test_every_source_has_a_name_a_shopper_would_recognise() -> None:
    assert source_label(EvidenceSource.RECEIPT) == "Verified receipts"
    assert {source_label(source) for source in EvidenceSource} == {
        "Partner data",
        "Verified receipts",
        "Online retailers",
        "Store visits",
        "Shelf photos",
        "Community reports",
    }


@pytest.mark.parametrize(
    ("price", "expected"),
    [
        (330.0, "cheap"),
        (336.5, "cheap"),
        (339.0, "fair"),
        (340.0, "fair"),
        (341.0, "fair"),
        (343.5, "high"),
        (380.0, "high"),
    ],
)
def test_a_store_is_only_cheap_or_dear_beyond_a_percent(price: float, expected: str) -> None:
    assert verdict_for(price, 340.0) == expected


def test_a_missing_market_price_leaves_every_store_fair() -> None:
    assert verdict_for(340.0, 0.0) == "fair"


def test_naive_timestamps_are_read_as_utc() -> None:
    naive = datetime(2026, 7, 25, 12, 0)

    assert as_utc(naive).tzinfo is timezone.utc
    assert as_utc(naive.replace(tzinfo=timezone.utc)) == naive.replace(tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_distance_is_measured_in_metres_by_the_database(session: AsyncSession) -> None:
    distance = distance_expression(SELAM_MART.latitude, SELAM_MART.longitude)
    rows = dict(
        (
            await session.execute(select(Store.name, distance).where(Store.name.in_(
                [SELAM_MART.name, CENTRAL.name]
            )))
        ).all()
    )

    assert rows[SELAM_MART.name] == pytest.approx(0, abs=1)
    # Piassa to Bole is a little under six kilometres.
    assert 4_000 < rows[CENTRAL.name] < 7_000


@pytest.mark.asyncio
async def test_fixture_mode_hands_routes_no_session() -> None:
    sessions = deps.optional_session()

    assert await anext(sessions) is None


@pytest.mark.asyncio
async def test_turning_fixtures_off_opens_a_session(monkeypatch: pytest.MonkeyPatch) -> None:
    opened = object()

    class Scope:
        async def __aenter__(self) -> object:
            return opened

        async def __aexit__(self, *_: object) -> None:
            return None

    monkeypatch.setattr(deps, "get_settings", lambda: SimpleNamespace(use_fixtures=False))
    monkeypatch.setattr(deps, "session_scope", Scope)

    sessions = deps.optional_session()
    assert await anext(sessions) is opened


def test_the_client_address_prefers_the_proxy_header() -> None:
    forwarded = SimpleNamespace(
        headers={"X-Forwarded-For": "41.86.1.1, 10.0.0.5"},
        client=SimpleNamespace(host="10.0.0.5"),
    )
    direct = SimpleNamespace(headers={}, client=SimpleNamespace(host="10.0.0.5"))
    anonymous = SimpleNamespace(headers={}, client=None)

    assert deps.client_ip(forwarded) == "41.86.1.1"
    assert deps.client_ip(direct) == "10.0.0.5"
    assert deps.client_ip(anonymous) == "unknown"
