"""Seed category_price_bounds for the fourteen supported categories.

The gate rejects outright anything outside these ranges, so they are
deliberately loose. A range covers every pack size sold in that unit, from a
sachet to a 25 kg sack or a 20 L jerrycan, because rejecting a legitimate bulk
pack costs a product its entire price history. Their job is catching a
fat-fingered 4200 ETB litre of oil, not judging a good deal; the deviation
check in `services/verification.py` does the precise work.

Revision ID: 20260725_0002
Revises: 20260725_0001
Create Date: 2026-07-25
"""

from collections.abc import Sequence
from decimal import Decimal
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260725_0002"
down_revision: str | None = "20260725_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# category, size_unit, min_etb, max_etb
BOUNDS: tuple[tuple[str, str, str, str], ...] = (
    ("cooking_oil", "ml", "25", "450"),
    ("cooking_oil", "l", "90", "3000"),
    ("sugar", "g", "12", "320"),
    ("sugar", "kg", "55", "3000"),
    ("rice", "g", "12", "300"),
    ("rice", "kg", "50", "4000"),
    ("flour", "g", "10", "240"),
    ("flour", "kg", "40", "3000"),
    ("salt", "g", "3", "80"),
    ("salt", "kg", "12", "400"),
    ("pasta", "g", "10", "260"),
    ("pasta", "kg", "40", "1000"),
    ("coffee", "g", "30", "1000"),
    ("coffee", "kg", "240", "3600"),
    ("tea", "g", "20", "700"),
    ("tea", "piece", "5", "300"),
    ("milk", "ml", "12", "300"),
    ("milk", "l", "35", "800"),
    ("soap", "g", "10", "300"),
    ("soap", "piece", "15", "300"),
    ("detergent", "g", "15", "450"),
    ("detergent", "kg", "100", "2500"),
    ("detergent", "ml", "15", "420"),
    ("detergent", "l", "90", "2000"),
    ("toothpaste", "g", "25", "500"),
    ("toothpaste", "ml", "25", "500"),
    ("toothpaste", "piece", "25", "500"),
    ("shampoo", "ml", "60", "1200"),
    ("shampoo", "l", "200", "2400"),
    ("bottled_water", "ml", "5", "120"),
    ("bottled_water", "l", "8", "400"),
)

bounds_table = sa.table(
    "category_price_bounds",
    sa.column("id", sa.Uuid()),
    sa.column("category", sa.String()),
    sa.column("size_unit", sa.String()),
    sa.column("min_etb", sa.Numeric(12, 2)),
    sa.column("max_etb", sa.Numeric(12, 2)),
)


def upgrade() -> None:
    op.bulk_insert(
        bounds_table,
        [
            {
                "id": uuid4(),
                "category": category,
                "size_unit": size_unit,
                "min_etb": Decimal(min_etb),
                "max_etb": Decimal(max_etb),
            }
            for category, size_unit, min_etb, max_etb in BOUNDS
        ],
    )


def downgrade() -> None:
    op.execute(bounds_table.delete())
