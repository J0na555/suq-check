"""Add MRP and out-of-stock evidence for Market Insights.

Revision ID: 20260726_0003
Revises: 20260725_0002
Create Date: 2026-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260726_0003"
down_revision: str | None = "20260725_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("product", sa.Column("mrp_etb", sa.Numeric(precision=12, scale=2), nullable=True))

    op.add_column(
        "evidence",
        sa.Column("is_oos", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.alter_column("evidence", "price_etb", existing_type=sa.Numeric(12, 2), nullable=True)
    op.drop_constraint("ck_evidence_positive_price", "evidence", type_="check")
    op.create_check_constraint(
        "ck_evidence_price_or_oos",
        "evidence",
        "(is_oos AND price_etb IS NULL) OR (NOT is_oos AND price_etb > 0)",
    )
    op.create_index("ix_evidence_is_oos", "evidence", ["is_oos"])


def downgrade() -> None:
    op.drop_index("ix_evidence_is_oos", table_name="evidence")
    op.drop_constraint("ck_evidence_price_or_oos", "evidence", type_="check")
    op.execute("DELETE FROM evidence WHERE is_oos OR price_etb IS NULL")
    op.alter_column("evidence", "price_etb", existing_type=sa.Numeric(12, 2), nullable=False)
    op.create_check_constraint("ck_evidence_positive_price", "evidence", "price_etb > 0")
    op.drop_column("evidence", "is_oos")
    op.drop_column("product", "mrp_etb")
