from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, LargeBinary, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ProductCategory, SizeUnit, enum_type


class Product(TimestampMixin, Base):
    __tablename__ = "product"
    __table_args__ = (
        UniqueConstraint(
            "brand",
            "canonical_name",
            "size_value",
            "size_unit",
            name="uq_product_identity",
        ),
        Index("ix_product_category", "category"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    canonical_name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[ProductCategory] = mapped_column(
        enum_type(ProductCategory, name="product_category"),
        nullable=False,
    )
    size_value: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    size_unit: Mapped[SizeUnit] = mapped_column(
        enum_type(SizeUnit, name="size_unit"),
        nullable=False,
    )
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True)
    thumbnail: Mapped[bytes | None] = mapped_column(LargeBinary)

    aliases: Mapped[list["ProductAlias"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )


class ProductAlias(TimestampMixin, Base):
    __tablename__ = "product_alias"
    __table_args__ = (
        UniqueConstraint("normalized_text", name="uq_product_alias_normalized_text"),
        Index("ix_product_alias_product_id", "product_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE"),
        nullable=False,
    )
    raw_text: Mapped[str] = mapped_column(String(300), nullable=False)
    normalized_text: Mapped[str] = mapped_column(String(300), nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)

    product: Mapped[Product] = relationship(back_populates="aliases")


Index(
    "ix_product_alias_normalized_trgm",
    ProductAlias.normalized_text,
    postgresql_using="gin",
    postgresql_ops={"normalized_text": "gin_trgm_ops"},
).ddl_if(dialect="postgresql")

