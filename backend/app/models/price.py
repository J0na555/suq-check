from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

JSON_DOCUMENT = JSON().with_variant(JSONB, "postgresql")


class PriceEstimate(Base):
    __tablename__ = "price_estimate"
    __table_args__ = (
        UniqueConstraint("product_id", "store_id", name="uq_price_estimate_product_store"),
        Index(
            "uq_price_estimate_market_product",
            "product_id",
            unique=True,
            postgresql_where=text("store_id IS NULL"),
            sqlite_where=text("store_id IS NULL"),
        ),
        CheckConstraint("price_etb > 0", name="positive_price"),
        CheckConstraint("confidence >= 0 AND confidence <= 100", name="confidence_range"),
        CheckConstraint("spread_pct >= 0", name="nonnegative_spread"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE"),
        nullable=False,
    )
    store_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("store.id", ondelete="CASCADE"),
    )
    price_etb: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    store_count: Mapped[int] = mapped_column(Integer, nullable=False)
    spread_pct: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    newest_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (
        UniqueConstraint("product_id", "day", name="uq_price_history_product_day"),
        CheckConstraint("price_etb > 0", name="positive_price"),
        CheckConstraint("evidence_count >= 0", name="nonnegative_evidence_count"),
        Index("ix_price_history_day", "day"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE"),
        nullable=False,
    )
    day: Mapped[date] = mapped_column(Date, nullable=False)
    price_etb: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)

