from uuid import UUID, uuid4

from sqlalchemy import Float, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import StoreKind, enum_type


class Store(TimestampMixin, Base):
    __tablename__ = "store"
    __table_args__ = (
        Index("ix_store_district", "district"),
        Index("ix_store_location", "latitude", "longitude"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    chain: Mapped[str | None] = mapped_column(String(120))
    district: Mapped[str] = mapped_column(String(120), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    kind: Mapped[StoreKind] = mapped_column(
        enum_type(StoreKind, name="store_kind"),
        nullable=False,
    )

