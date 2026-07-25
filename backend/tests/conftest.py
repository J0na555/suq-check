"""A seeded SQLite database shared by the tests that need real rows.

Seeding is the slow part, so it happens once per session against a file, and
each test opens its own engine over that file. The category bounds come from the
migration that ships them, so the gate is tested against the real ranges.
"""

import asyncio
import importlib.util
import shutil
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.deps import optional_session
from app.main import app
from app.models import Base, CategoryPriceBounds
from app.repositories import pulse
from app.seed import read_products, read_stores, seed_database
from app.services import rate_limit

SQLITE_PREFIX = "sqlite+aiosqlite:///"

BACKEND_DIR = Path(__file__).resolve().parents[1]
BOUNDS_MIGRATION = (
    BACKEND_DIR / "migrations" / "versions" / "20260725_0002_seed_category_price_bounds.py"
)

# Frozen so history, freshness, and the staleness cap are the same every run.
SEED_NOW = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)


def _migration_bounds() -> tuple[tuple[str, str, str, str], ...]:
    spec = importlib.util.spec_from_file_location("bounds_migration", BOUNDS_MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BOUNDS


async def _build(url: str) -> None:
    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        session.add_all(
            [
                CategoryPriceBounds(
                    category=category,
                    size_unit=size_unit,
                    min_etb=Decimal(minimum),
                    max_etb=Decimal(maximum),
                )
                for category, size_unit, minimum, maximum in _migration_bounds()
            ]
        )
        await session.flush()
        await seed_database(
            session,
            products=read_products(),
            stores=read_stores(),
            now=SEED_NOW,
        )
        await session.commit()

    await engine.dispose()


@pytest.fixture(scope="session")
def seeded_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    path = tmp_path_factory.mktemp("suqcheck") / "seeded.sqlite"
    url = f"{SQLITE_PREFIX}{path}"
    asyncio.run(_build(url))
    return url


@pytest.fixture
def writable_url(seeded_url: str, tmp_path: Path) -> str:
    """A private copy, so tests that ingest cannot disturb tests that only read."""
    copy = tmp_path / "writable.sqlite"
    shutil.copy(seeded_url.removeprefix(SQLITE_PREFIX), copy)
    return f"{SQLITE_PREFIX}{copy}"


@pytest.fixture
async def session(seeded_url: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(seeded_url)
    async with async_sessionmaker(engine, expire_on_commit=False)() as opened:
        yield opened
    await engine.dispose()


@pytest.fixture
async def writable_session(writable_url: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(writable_url)
    async with async_sessionmaker(engine, expire_on_commit=False)() as opened:
        yield opened
    await engine.dispose()


@contextmanager
def _running_app(url: str) -> Iterator[TestClient]:
    """The app with fixtures switched off, reading the given database."""
    # NullPool closes each connection with its session, inside the loop that
    # opened it, so nothing is left for the synchronous teardown to close.
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override() -> AsyncIterator[AsyncSession]:
        async with factory() as opened:
            yield opened

    pulse.clear_cache()
    rate_limit.reset()
    app.dependency_overrides[optional_session] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    pulse.clear_cache()
    rate_limit.reset()
    engine.sync_engine.dispose()


@pytest.fixture
def database_client(seeded_url: str) -> Iterator[TestClient]:
    with _running_app(seeded_url) as client:
        yield client


@pytest.fixture
def writing_client(writable_url: str) -> Iterator[TestClient]:
    with _running_app(writable_url) as client:
        yield client
