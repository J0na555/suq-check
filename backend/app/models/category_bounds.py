from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Numeric, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import ProductCategory, SizeUnit, enum_type


class CategoryPriceBounds(TimestampMixin, Base):
    __tablename__ = "category_price_bounds"
    __table_args__ = (
        UniqueConstraint("category", "size_unit", name="uq_category_bounds_category_unit"),
        CheckConstraint("min_etb > 0", name="positive_min_price"),
        CheckConstraint("max_etb >= min_etb", name="valid_price_range"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    category: Mapped[ProductCategory] = mapped_column(
        enum_type(ProductCategory, name="bounds_product_category"),
        nullable=False,
    )
    size_unit: Mapped[SizeUnit] = mapped_column(
        enum_type(SizeUnit, name="bounds_size_unit"),
        nullable=False,
    )
    min_etb: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    max_etb: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

