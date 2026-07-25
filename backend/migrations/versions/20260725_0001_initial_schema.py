"""Create the evidence-backed pricing schema.

Revision ID: 20260725_0001
Revises:
Create Date: 2026-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260725_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "product",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("canonical_name", sa.String(length=200), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=13), nullable=False),
        sa.Column("size_value", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("size_unit", sa.String(length=5), nullable=False),
        sa.Column("barcode", sa.String(length=64), nullable=True),
        sa.Column("thumbnail", sa.LargeBinary(), nullable=True),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_product"),
        sa.UniqueConstraint("barcode", name="uq_product_barcode"),
        sa.UniqueConstraint(
            "brand",
            "canonical_name",
            "size_value",
            "size_unit",
            name="uq_product_identity",
        ),
    )
    op.create_index("ix_product_category", "product", ["category"])

    op.create_table(
        "store",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("chain", sa.String(length=120), nullable=True),
        sa.Column("district", sa.String(length=120), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("kind", sa.String(length=11), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_store"),
    )
    op.create_index("ix_store_district", "store", ["district"])
    op.create_index("ix_store_location", "store", ["latitude", "longitude"])

    op.create_table(
        "category_price_bounds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=13), nullable=False),
        sa.Column("size_unit", sa.String(length=5), nullable=False),
        sa.Column("min_etb", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("max_etb", sa.Numeric(precision=12, scale=2), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("max_etb >= min_etb", name="ck_category_price_bounds_valid_price_range"),
        sa.CheckConstraint("min_etb > 0", name="ck_category_price_bounds_positive_min_price"),
        sa.PrimaryKeyConstraint("id", name="pk_category_price_bounds"),
        sa.UniqueConstraint(
            "category",
            "size_unit",
            name="uq_category_bounds_category_unit",
        ),
    )

    op.create_table(
        "product_alias",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("raw_text", sa.String(length=300), nullable=False),
        sa.Column("normalized_text", sa.String(length=300), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
            name="fk_product_alias_product_id_product",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_product_alias"),
        sa.UniqueConstraint(
            "normalized_text",
            name="uq_product_alias_normalized_text",
        ),
    )
    op.create_index("ix_product_alias_product_id", "product_alias", ["product_id"])
    op.create_index(
        "ix_product_alias_normalized_trgm",
        "product_alias",
        ["normalized_text"],
        postgresql_using="gin",
        postgresql_ops={"normalized_text": "gin_trgm_ops"},
    )

    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=True),
        sa.Column("price_etb", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("source_type", sa.String(length=11), nullable=False),
        sa.Column("ocr_confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("thumbnail", sa.LargeBinary(), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint(
            "ocr_confidence >= 0 AND ocr_confidence <= 1",
            name="ck_evidence_ocr_confidence_range",
        ),
        sa.CheckConstraint("price_etb > 0", name="ck_evidence_positive_price"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
            name="fk_evidence_product_id_product",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["store.id"],
            name="fk_evidence_store_id_store",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evidence"),
    )
    op.create_index(
        "ix_evidence_product_observed",
        "evidence",
        ["product_id", "observed_at"],
    )
    op.create_index(
        "ix_evidence_store_observed",
        "evidence",
        ["store_id", "observed_at"],
    )
    op.create_index("ix_evidence_status", "evidence", ["status"])

    op.create_table(
        "price_estimate",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=True),
        sa.Column("price_etb", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("store_count", sa.Integer(), nullable=False),
        sa.Column("spread_pct", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("newest_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 100",
            name="ck_price_estimate_confidence_range",
        ),
        sa.CheckConstraint(
            "spread_pct >= 0",
            name="ck_price_estimate_nonnegative_spread",
        ),
        sa.CheckConstraint("price_etb > 0", name="ck_price_estimate_positive_price"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
            name="fk_price_estimate_product_id_product",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["store.id"],
            name="fk_price_estimate_store_id_store",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_price_estimate"),
        sa.UniqueConstraint(
            "product_id",
            "store_id",
            name="uq_price_estimate_product_store",
        ),
    )
    op.create_index(
        "uq_price_estimate_market_product",
        "price_estimate",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("store_id IS NULL"),
    )

    op.create_table(
        "price_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("price_etb", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "evidence_count >= 0",
            name="ck_price_history_nonnegative_evidence_count",
        ),
        sa.CheckConstraint("price_etb > 0", name="ck_price_history_positive_price"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
            name="fk_price_history_product_id_product",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_price_history"),
        sa.UniqueConstraint(
            "product_id",
            "day",
            name="uq_price_history_product_day",
        ),
    )
    op.create_index("ix_price_history_day", "price_history", ["day"])


def downgrade() -> None:
    op.drop_index("ix_price_history_day", table_name="price_history")
    op.drop_table("price_history")
    op.drop_index("uq_price_estimate_market_product", table_name="price_estimate")
    op.drop_table("price_estimate")
    op.drop_index("ix_evidence_status", table_name="evidence")
    op.drop_index("ix_evidence_store_observed", table_name="evidence")
    op.drop_index("ix_evidence_product_observed", table_name="evidence")
    op.drop_table("evidence")
    op.drop_index("ix_product_alias_normalized_trgm", table_name="product_alias")
    op.drop_index("ix_product_alias_product_id", table_name="product_alias")
    op.drop_table("product_alias")
    op.drop_table("category_price_bounds")
    op.drop_index("ix_store_location", table_name="store")
    op.drop_index("ix_store_district", table_name="store")
    op.drop_table("store")
    op.drop_index("ix_product_category", table_name="product")
    op.drop_table("product")

