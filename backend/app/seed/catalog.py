"""Read the two researched CSVs in `data/` into validated rows.

The non-coders own those files, so every failure names the file, the row, and
the column, and lists the values that would have been accepted.
"""

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from uuid import UUID, uuid5

from app.models.enums import ProductCategory, SizeUnit, StoreKind

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
PRODUCTS_CSV = DATA_DIR / "products.csv"
STORES_CSV = DATA_DIR / "stores.csv"

# Deriving ids from the catalog identity keeps them stable across re-seeds, so a
# bookmarked product URL survives a reset.
ID_NAMESPACE = UUID("2f2d4c1e-9b7a-4d0e-8a63-1f5f8c6b7a10")

PRODUCT_COLUMNS = (
    "canonical_name",
    "brand",
    "category",
    "size_value",
    "size_unit",
    "barcode",
    "base_price_etb",
    "coverage",
)
STORE_COLUMNS = ("name", "chain", "district", "latitude", "longitude", "kind")


class SeedDataError(ValueError):
    """A CSV row the seed cannot use."""


class Coverage(StrEnum):
    """How much evidence the generator invents for a product."""

    RICH = "rich"
    NORMAL = "normal"
    THIN = "thin"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class ProductRow:
    id: UUID
    canonical_name: str
    brand: str
    category: ProductCategory
    size_value: float
    size_unit: SizeUnit
    barcode: str | None
    base_price_etb: float
    coverage: Coverage


@dataclass(frozen=True, slots=True)
class StoreRow:
    id: UUID
    name: str
    chain: str | None
    district: str
    latitude: float
    longitude: float
    kind: StoreKind


def product_id(brand: str, canonical_name: str, size_value: float, size_unit: SizeUnit) -> UUID:
    identity = f"product:{brand.strip().casefold()}|{canonical_name.strip().casefold()}"
    return uuid5(ID_NAMESPACE, f"{identity}|{size_value:g}{size_unit.value}")


def store_id(name: str, district: str) -> UUID:
    return uuid5(ID_NAMESPACE, f"store:{name.strip().casefold()}|{district.strip().casefold()}")


def _rows(path: Path, columns: tuple[str, ...]) -> Iterator[tuple[int, dict[str, str]]]:
    if not path.is_file():
        raise SeedDataError(f"{_where(path)} does not exist; copy the committed example file")

    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in columns if column not in (reader.fieldnames or ())]
        if missing:
            raise SeedDataError(f"{_where(path)} is missing the {', '.join(missing)} column(s)")
        for number, row in enumerate(reader, start=2):
            if any((value or "").strip() for value in row.values()):
                yield number, row


def _where(path: Path, number: int | None = None) -> str:
    try:
        label = path.relative_to(DATA_DIR.parent).as_posix()
    except ValueError:
        label = path.as_posix()
    return label if number is None else f"{label} row {number}"


def _text(path: Path, number: int, row: dict[str, str], column: str, *, required: bool) -> str:
    value = (row.get(column) or "").strip()
    if not value and required:
        raise SeedDataError(f"{_where(path, number)}: {column} is required")
    return value


def _number(path: Path, number: int, row: dict[str, str], column: str) -> float:
    value = _text(path, number, row, column, required=True)
    try:
        return float(value)
    except ValueError as error:
        raise SeedDataError(
            f"{_where(path, number)}: {column} must be a number, not {value!r}"
        ) from error


def _choice[Member: StrEnum](
    path: Path,
    number: int,
    row: dict[str, str],
    column: str,
    options: type[Member],
) -> Member:
    value = _text(path, number, row, column, required=True).casefold()
    try:
        return options(value)
    except ValueError as error:
        allowed = ", ".join(member.value for member in options)
        raise SeedDataError(
            f"{_where(path, number)}: {column} is {value!r}, expected one of {allowed}"
        ) from error


def read_products(path: Path = PRODUCTS_CSV) -> list[ProductRow]:
    products: list[ProductRow] = []
    for number, row in _rows(path, PRODUCT_COLUMNS):
        size_unit = _choice(path, number, row, "size_unit", SizeUnit)
        size_value = _number(path, number, row, "size_value")
        base_price = _number(path, number, row, "base_price_etb")
        if size_value <= 0:
            raise SeedDataError(f"{_where(path, number)}: size_value must be above zero")
        if base_price <= 0:
            raise SeedDataError(f"{_where(path, number)}: base_price_etb must be above zero")

        canonical_name = _text(path, number, row, "canonical_name", required=True)
        brand = _text(path, number, row, "brand", required=True)
        products.append(
            ProductRow(
                id=product_id(brand, canonical_name, size_value, size_unit),
                canonical_name=canonical_name,
                brand=brand,
                category=_choice(path, number, row, "category", ProductCategory),
                size_value=size_value,
                size_unit=size_unit,
                barcode=_text(path, number, row, "barcode", required=False) or None,
                base_price_etb=base_price,
                coverage=_choice(path, number, row, "coverage", Coverage),
            )
        )

    _reject_duplicates(path, [product.id for product in products], "product")
    return products


def read_stores(path: Path = STORES_CSV) -> list[StoreRow]:
    stores: list[StoreRow] = []
    for number, row in _rows(path, STORE_COLUMNS):
        latitude = _number(path, number, row, "latitude")
        longitude = _number(path, number, row, "longitude")
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise SeedDataError(
                f"{_where(path, number)}: {latitude}, {longitude} is not a valid coordinate"
            )

        name = _text(path, number, row, "name", required=True)
        district = _text(path, number, row, "district", required=True)
        stores.append(
            StoreRow(
                id=store_id(name, district),
                name=name,
                chain=_text(path, number, row, "chain", required=False) or None,
                district=district,
                latitude=latitude,
                longitude=longitude,
                kind=_choice(path, number, row, "kind", StoreKind),
            )
        )

    _reject_duplicates(path, [store.id for store in stores], "store")
    return stores


def _reject_duplicates(path: Path, ids: list[UUID], label: str) -> None:
    if len(set(ids)) != len(ids):
        raise SeedDataError(f"{_where(path)} lists the same {label} twice")
