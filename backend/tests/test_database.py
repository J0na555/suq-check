from decimal import Decimal

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import async_database_url
from app.models import Base, Product
from app.models.enums import ProductCategory, SizeUnit

EXPECTED_TABLES = {
    "category_price_bounds",
    "evidence",
    "price_estimate",
    "price_history",
    "product",
    "product_alias",
    "store",
}


def test_postgres_url_is_converted_for_asyncpg() -> None:
    result = async_database_url(
        "postgresql://suqcheck:secret@example.neon.tech/neondb"
        "?sslmode=require&channel_binding=require"
    )

    assert result.drivername == "postgresql+asyncpg"
    assert result.host == "example.neon.tech"
    assert result.query["ssl"] == "require"
    assert "sslmode" not in result.query
    assert "channel_binding" not in result.query


def test_empty_database_url_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        async_database_url("")


def test_metadata_contains_the_planned_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_market_estimate_has_partial_unique_index() -> None:
    table = Base.metadata.tables["price_estimate"]
    index = next(item for item in table.indexes if item.name == "uq_price_estimate_market_product")

    assert index.unique is True
    assert str(index.dialect_options["postgresql"]["where"]) == "store_id IS NULL"


@pytest.mark.asyncio
async def test_schema_and_models_work_with_async_sessions() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        table_names = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_table_names()
        )

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        product = Product(
            canonical_name="Hayat Cooking Oil 1L",
            brand="Hayat",
            category=ProductCategory.COOKING_OIL,
            size_value=Decimal("1"),
            size_unit=SizeUnit.LITER,
        )
        session.add(product)
        await session.commit()

        saved = await session.scalar(select(Product).where(Product.id == product.id))

    assert set(table_names) == EXPECTED_TABLES
    assert saved is not None
    assert saved.category == ProductCategory.COOKING_OIL

    await engine.dispose()

