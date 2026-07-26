from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import EvidenceSource, EvidenceStatus, enum_type

JSON_DOCUMENT = JSON().with_variant(JSONB, "postgresql")


class Evidence(TimestampMixin, Base):
    __tablename__ = "evidence"
    __table_args__ = (
        CheckConstraint(
            "(is_oos AND price_etb IS NULL) OR (NOT is_oos AND price_etb > 0)",
            name="evidence_price_or_oos",
        ),
        CheckConstraint(
            "ocr_confidence >= 0 AND ocr_confidence <= 1",
            name="ocr_confidence_range",
        ),
        Index("ix_evidence_product_observed", "product_id", "observed_at"),
        Index("ix_evidence_store_observed", "store_id", "observed_at"),
        Index("ix_evidence_status", "status"),
        Index("ix_evidence_is_oos", "is_oos"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE"),
        nullable=False,
    )
    store_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("store.id", ondelete="SET NULL"),
    )
    price_etb: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    is_oos: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_type: Mapped[EvidenceSource] = mapped_column(
        enum_type(EvidenceSource, name="evidence_source"),
        nullable=False,
    )
    ocr_confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=1,
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[EvidenceStatus] = mapped_column(
        enum_type(EvidenceStatus, name="evidence_status"),
        nullable=False,
        default=EvidenceStatus.PENDING,
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(500))
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT,
        nullable=False,
        default=dict,
    )
    thumbnail: Mapped[bytes | None] = mapped_column(LargeBinary)
