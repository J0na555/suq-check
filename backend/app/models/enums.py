from enum import StrEnum
from typing import TypeVar

from sqlalchemy import Enum

EnumType = TypeVar("EnumType", bound=StrEnum)


def enum_type(enum_class: type[EnumType], *, name: str) -> Enum:
    return Enum(
        enum_class,
        values_callable=lambda members: [member.value for member in members],
        name=name,
        native_enum=False,
        validate_strings=True,
    )


class ProductCategory(StrEnum):
    COOKING_OIL = "cooking_oil"
    SUGAR = "sugar"
    RICE = "rice"
    FLOUR = "flour"
    SALT = "salt"
    PASTA = "pasta"
    COFFEE = "coffee"
    TEA = "tea"
    MILK = "milk"
    SOAP = "soap"
    DETERGENT = "detergent"
    TOOTHPASTE = "toothpaste"
    SHAMPOO = "shampoo"
    BOTTLED_WATER = "bottled_water"


class SizeUnit(StrEnum):
    MILLILITER = "ml"
    LITER = "l"
    GRAM = "g"
    KILOGRAM = "kg"
    PIECE = "piece"


class StoreKind(StrEnum):
    SUPERMARKET = "supermarket"
    SHOP = "shop"
    ONLINE = "online"


class EvidenceSource(StrEnum):
    PARTNER = "partner"
    RECEIPT = "receipt"
    SCRAPE = "scrape"
    STORE_VISIT = "store_visit"
    SHELF_PHOTO = "shelf_photo"
    COMMUNITY = "community"


class EvidenceStatus(StrEnum):
    ACCEPTED = "accepted"
    PENDING = "pending"
    REJECTED = "rejected"

