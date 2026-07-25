"""Turn stored rows into the words and shapes the contract promises.

Everything the API says about a price beyond the number itself lives here:
the size on the label, the name of a source, and whether a store is cheap.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from sqlalchemy import ColumnElement, func

from app.models.enums import EvidenceSource, SizeUnit
from app.models.product import Product
from app.models.store import Store
from app.schemas.products import ProductSummary
from app.services.price_engine import band_for

Verdict = Literal["cheap", "fair", "high"]

EARTH_RADIUS_M = 6_371_000

# A store is only called cheap or dear once it is a full percent off the market
# price; anything tighter is rounding, not a reason to walk further.
VERDICT_TOLERANCE = 0.01

SIZE_UNIT_LABELS: dict[SizeUnit, str] = {
    SizeUnit.MILLILITER: "ml",
    SizeUnit.LITER: "L",
    SizeUnit.GRAM: "g",
    SizeUnit.KILOGRAM: "kg",
    SizeUnit.PIECE: "piece",
}

SOURCE_LABELS: dict[EvidenceSource, str] = {
    EvidenceSource.PARTNER: "Partner data",
    EvidenceSource.RECEIPT: "Verified receipts",
    EvidenceSource.SCRAPE: "Online retailers",
    EvidenceSource.STORE_VISIT: "Store visits",
    EvidenceSource.SHELF_PHOTO: "Shelf photos",
    EvidenceSource.COMMUNITY: "Community reports",
}


def as_utc(moment: datetime) -> datetime:
    """SQLite hands back naive datetimes; the contract promises an offset."""
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def size_label(value: Decimal | float, unit: SizeUnit) -> str:
    """`1 L`, `175 g`, `1.5 L`: the size as it reads on the pack."""
    number = f"{float(value):.3f}".rstrip("0").rstrip(".")
    return f"{number} {SIZE_UNIT_LABELS[unit]}"


def source_label(source: EvidenceSource) -> str:
    return SOURCE_LABELS[source]


def verdict_for(price_etb: float, market_price_etb: float) -> Verdict:
    if market_price_etb <= 0:
        return "fair"
    difference = (price_etb - market_price_etb) / market_price_etb
    if difference <= -VERDICT_TOLERANCE:
        return "cheap"
    if difference >= VERDICT_TOLERANCE:
        return "high"
    return "fair"


def distance_expression(latitude: float, longitude: float) -> ColumnElement[float]:
    """Great-circle metres from a point to `store`, computed by the database."""
    from_latitude = func.radians(latitude)
    from_longitude = func.radians(longitude)
    to_latitude = func.radians(Store.latitude)
    to_longitude = func.radians(Store.longitude)
    chord = func.power(func.sin((to_latitude - from_latitude) / 2), 2) + func.cos(
        from_latitude
    ) * func.cos(to_latitude) * func.power(func.sin((to_longitude - from_longitude) / 2), 2)
    return 2 * EARTH_RADIUS_M * func.asin(func.sqrt(chord))


def product_summary(product: Product, price_etb: Decimal, confidence: int) -> ProductSummary:
    """The list-row shape shared by search results and product detail."""
    return ProductSummary(
        id=product.id,
        canonical_name=product.canonical_name,
        brand=product.brand,
        category=product.category.value,
        size_label=size_label(product.size_value, product.size_unit),
        market_price_etb=float(price_etb),
        confidence=confidence,
        confidence_band=band_for(confidence),
        thumbnail_url=None,
    )
