"""`python -m app.seed` fills the configured database from `data/*.csv`."""

import argparse
import asyncio
from pathlib import Path

from app.database import close_database, session_scope
from app.seed.catalog import PRODUCTS_CSV, STORES_CSV, SeedDataError, read_products, read_stores
from app.seed.runner import backfill_mrp, seed_database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--products", type=Path, default=PRODUCTS_CSV)
    parser.add_argument("--stores", type=Path, default=STORES_CSV)
    parser.add_argument(
        "--mrp-only",
        action="store_true",
        help="Only backfill product.mrp_etb from the products CSV; leave evidence alone.",
    )
    return parser.parse_args()


async def run(products_csv: Path, stores_csv: Path, *, mrp_only: bool) -> None:
    products = read_products(products_csv)

    async with session_scope() as session:
        if mrp_only:
            updated = await backfill_mrp(session, products=products)
            await session.commit()
            print(f"Updated mrp_etb on {updated} products")
        else:
            stores = read_stores(stores_csv)
            summary = await seed_database(session, products=products, stores=stores)
            await session.commit()
            for line in summary.lines():
                print(line)

    await close_database()


def main() -> int:
    arguments = parse_args()
    try:
        asyncio.run(
            run(arguments.products, arguments.stores, mrp_only=arguments.mrp_only)
        )
    except SeedDataError as error:
        print(f"Seed data problem: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
