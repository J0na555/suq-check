"""Market Insights analytics: MRP compliance, districts, OOS, competitors."""

from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Literal
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EvidenceStatus, ProductCategory
from app.models.evidence import Evidence
from app.models.price import PriceEstimate
from app.models.product import Product
from app.models.store import Store
from app.repositories.analytics import price_changes
from app.schemas.analytics import (
    CompetitorRow,
    CompetitorsResponse,
    ComplianceBand,
    ComplianceResponse,
    ComplianceRow,
    ComplianceSummary,
    DistrictRow,
    DistrictsResponse,
    OosAlert,
    OosResponse,
)

# Within this band of MRP a shelf price counts as compliant.
MRP_TOLERANCE = 0.02
OOS_LOOKBACK_DAYS = 7


def compliance_band(price_etb: float, mrp_etb: float) -> ComplianceBand:
    if mrp_etb <= 0:
        return "at"
    delta = (price_etb - mrp_etb) / mrp_etb
    if abs(delta) <= MRP_TOLERANCE:
        return "at"
    return "above" if delta > 0 else "below"


def _pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round(100 * part / whole, 1)


async def load_compliance(
    session: AsyncSession,
    *,
    category: str | None = None,
    brand: str | None = None,
) -> ComplianceResponse:
    filters = [
        PriceEstimate.store_id.is_not(None),
        Product.mrp_etb.is_not(None),
    ]
    if category:
        filters.append(Product.category == ProductCategory(category))
    if brand:
        filters.append(Product.brand.ilike(brand.strip()))

    store_rows = (
        await session.execute(
            select(
                Product.id,
                Product.canonical_name,
                Product.brand,
                Product.category,
                Product.mrp_etb,
                PriceEstimate.price_etb,
            )
            .join(Product, Product.id == PriceEstimate.product_id)
            .where(*filters)
        )
    ).all()

    market_rows = (
        await session.execute(
            select(
                Product.id,
                Product.canonical_name,
                Product.brand,
                Product.category,
                Product.mrp_etb,
                PriceEstimate.price_etb,
                PriceEstimate.store_count,
            )
            .join(Product, Product.id == PriceEstimate.product_id)
            .where(
                PriceEstimate.store_id.is_(None),
                Product.mrp_etb.is_not(None),
                *(
                    [Product.category == ProductCategory(category)]
                    if category
                    else []
                ),
                *([Product.brand.ilike(brand.strip())] if brand else []),
            )
        )
    ).all()

    by_product: dict[
        UUID,
        dict[str, int | float | str | ProductCategory],
    ] = {}
    totals = {"at": 0, "above": 0, "below": 0}

    for product_id, name, brand_name, cat, mrp, price in store_rows:
        mrp_value = float(mrp)
        band = compliance_band(float(price), mrp_value)
        totals[band] += 1
        bucket = by_product.setdefault(
            product_id,
            {
                "name": name,
                "brand": brand_name,
                "category": cat,
                "mrp": mrp_value,
                "at": 0,
                "above": 0,
                "below": 0,
            },
        )
        bucket[band] = int(bucket[band]) + 1

    market_by_id = {
        product_id: (name, brand_name, cat, float(mrp), float(price), store_count)
        for product_id, name, brand_name, cat, mrp, price, store_count in market_rows
    }

    items: list[ComplianceRow] = []
    for product_id, market in market_by_id.items():
        name, brand_name, cat, mrp_value, market_price, store_count = market
        shop = by_product.get(product_id, {"at": 0, "above": 0, "below": 0})
        delta_pct = round(100 * (market_price - mrp_value) / mrp_value, 1) if mrp_value else 0.0
        items.append(
            ComplianceRow(
                product_id=product_id,
                product_name=name,
                brand=brand_name,
                category=cat.value,
                mrp_etb=mrp_value,
                market_price_etb=market_price,
                delta_pct=delta_pct,
                band=compliance_band(market_price, mrp_value),
                store_count=store_count,
                at_mrp=int(shop["at"]),
                above_mrp=int(shop["above"]),
                below_mrp=int(shop["below"]),
            )
        )

    items.sort(key=lambda row: abs(row.delta_pct), reverse=True)
    priced = totals["at"] + totals["above"] + totals["below"]
    return ComplianceResponse(
        summary=ComplianceSummary(
            shops_priced=priced,
            at_mrp=totals["at"],
            above_mrp=totals["above"],
            below_mrp=totals["below"],
            at_pct=_pct(totals["at"], priced),
            above_pct=_pct(totals["above"], priced),
            below_pct=_pct(totals["below"], priced),
        ),
        items=items,
    )


async def load_districts(
    session: AsyncSession,
    *,
    category: str | None = None,
    product_id: UUID | None = None,
    now: datetime | None = None,
) -> DistrictsResponse:
    moment = now or datetime.now(timezone.utc)
    oos_since = moment - timedelta(days=OOS_LOOKBACK_DAYS)

    price_filters = [PriceEstimate.store_id.is_not(None), Product.mrp_etb.is_not(None)]
    if category:
        price_filters.append(Product.category == ProductCategory(category))
    if product_id:
        price_filters.append(Product.id == product_id)

    price_rows = (
        await session.execute(
            select(
                Store.district,
                func.avg(PriceEstimate.price_etb),
                func.avg(Product.mrp_etb),
                func.count(),
                func.sum(
                    case(
                        (
                            and_(
                                PriceEstimate.price_etb
                                >= Product.mrp_etb * (1 - MRP_TOLERANCE),
                                PriceEstimate.price_etb
                                <= Product.mrp_etb * (1 + MRP_TOLERANCE),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
            )
            .join(Store, Store.id == PriceEstimate.store_id)
            .join(Product, Product.id == PriceEstimate.product_id)
            .where(*price_filters)
            .group_by(Store.district)
        )
    ).all()

    oos_filters = [
        Evidence.is_oos.is_(True),
        Evidence.status == EvidenceStatus.ACCEPTED,
        Evidence.observed_at >= oos_since,
        Evidence.store_id.is_not(None),
    ]
    if category:
        oos_filters.append(Product.category == ProductCategory(category))
    if product_id:
        oos_filters.append(Product.id == product_id)

    oos_rows = (
        await session.execute(
            select(Store.district, func.count())
            .join(Evidence, Evidence.store_id == Store.id)
            .join(Product, Product.id == Evidence.product_id)
            .where(*oos_filters)
            .group_by(Store.district)
        )
    ).all()
    oos_by_district = {district: count for district, count in oos_rows}

    items: list[DistrictRow] = []
    for district, avg_price, avg_mrp, priced, at_count in price_rows:
        avg_price_etb = float(avg_price or 0)
        avg_mrp_etb = None if avg_mrp is None else float(avg_mrp)
        oos_cells = int(oos_by_district.get(district, 0))
        priced_cells = int(priced or 0)
        resolved = priced_cells + oos_cells
        vs_mrp = (
            None
            if avg_mrp_etb is None or avg_mrp_etb <= 0
            else round(100 * (avg_price_etb - avg_mrp_etb) / avg_mrp_etb, 1)
        )
        items.append(
            DistrictRow(
                district=district,
                avg_price_etb=round(avg_price_etb, 2),
                avg_mrp_etb=None if avg_mrp_etb is None else round(avg_mrp_etb, 2),
                vs_mrp_pct=vs_mrp,
                priced_cells=priced_cells,
                oos_cells=oos_cells,
                oos_rate_pct=_pct(oos_cells, resolved),
                at_mrp_pct=_pct(int(at_count or 0), priced_cells),
            )
        )

    items.sort(key=lambda row: row.district)
    return DistrictsResponse(items=items)


async def load_oos_alerts(
    session: AsyncSession,
    *,
    category: str | None = None,
    days: int = OOS_LOOKBACK_DAYS,
    now: datetime | None = None,
    limit: int = 100,
) -> OosResponse:
    moment = now or datetime.now(timezone.utc)
    filters = [
        Evidence.is_oos.is_(True),
        Evidence.status == EvidenceStatus.ACCEPTED,
        Evidence.observed_at >= moment - timedelta(days=days),
    ]
    if category:
        filters.append(Product.category == ProductCategory(category))

    total = await session.scalar(
        select(func.count())
        .select_from(Evidence)
        .join(Product, Product.id == Evidence.product_id)
        .where(*filters)
    )

    rows = (
        await session.execute(
            select(
                Evidence.id,
                Evidence.product_id,
                Product.canonical_name,
                Product.brand,
                Product.category,
                Evidence.store_id,
                Store.name,
                Store.district,
                Evidence.observed_at,
                Evidence.source_type,
            )
            .join(Product, Product.id == Evidence.product_id)
            .outerjoin(Store, Store.id == Evidence.store_id)
            .where(*filters)
            .order_by(Evidence.observed_at.desc())
            .limit(limit)
        )
    ).all()

    return OosResponse(
        period_days=days,
        total=total or 0,
        items=[
            OosAlert(
                id=evidence_id,
                product_id=product_id,
                product_name=name,
                brand=brand,
                category=category_value.value,
                store_id=store_id,
                store_name=store_name,
                district=district,
                observed_at=observed_at
                if observed_at.tzinfo
                else observed_at.replace(tzinfo=timezone.utc),
                source_type=source.value,
            )
            for (
                evidence_id,
                product_id,
                name,
                brand,
                category_value,
                store_id,
                store_name,
                district,
                observed_at,
                source,
            ) in rows
        ],
    )


async def load_competitors(
    session: AsyncSession,
    *,
    category: str | None = None,
    now: datetime | None = None,
) -> CompetitorsResponse:
    moment = now or datetime.now(timezone.utc)
    filters = [PriceEstimate.store_id.is_(None)]
    if category:
        filters.append(Product.category == ProductCategory(category))

    rows = (
        await session.execute(
            select(
                Product.id,
                Product.canonical_name,
                Product.brand,
                Product.category,
                Product.mrp_etb,
                PriceEstimate.price_etb,
                PriceEstimate.store_count,
                PriceEstimate.confidence,
            )
            .join(PriceEstimate, PriceEstimate.product_id == Product.id)
            .where(*filters)
            .order_by(Product.brand, Product.canonical_name)
        )
    ).all()

    prices = [float(row[5]) for row in rows]
    category_median = round(median(prices), 2) if prices else None

    changes = {
        change.product_id: change
        for change in await price_changes(session, period_days=7, now=moment)
    }

    items: list[CompetitorRow] = []
    for (
        product_id,
        name,
        brand,
        cat,
        mrp,
        price,
        store_count,
        confidence,
    ) in rows:
        market_price = float(price)
        vs_median = (
            0.0
            if category_median is None or category_median <= 0
            else round(100 * (market_price - category_median) / category_median, 1)
        )
        change = changes.get(product_id)
        items.append(
            CompetitorRow(
                product_id=product_id,
                product_name=name,
                brand=brand,
                category=cat.value,
                market_price_etb=market_price,
                mrp_etb=None if mrp is None else float(mrp),
                vs_category_median_pct=vs_median,
                change_pct=0.0 if change is None else change.change_pct,
                direction="stable" if change is None else change.direction,
                store_count=store_count,
                confidence=confidence,
            )
        )

    items.sort(key=lambda row: abs(row.vs_category_median_pct), reverse=True)
    return CompetitorsResponse(
        category=category,  # type: ignore[arg-type]
        category_median_etb=category_median,
        items=items,
    )


async def insights_summary_metrics(
    session: AsyncSession,
    *,
    now: datetime | None = None,
) -> tuple[float, float, int, int]:
    """Return compliance %, OOS rate %, categories covered, active OOS alerts."""
    moment = now or datetime.now(timezone.utc)
    compliance = await load_compliance(session)
    oos = await load_oos_alerts(session, days=OOS_LOOKBACK_DAYS, now=moment, limit=1)

    priced = compliance.summary.shops_priced
    oos_total = oos.total
    resolved = priced + oos_total
    oos_rate = _pct(oos_total, resolved) if resolved else 0.0

    categories = await session.scalar(
        select(func.count(func.distinct(Product.category)))
        .select_from(Product)
        .join(PriceEstimate, PriceEstimate.product_id == Product.id)
        .where(PriceEstimate.store_id.is_(None))
    )

    return (
        compliance.summary.at_pct,
        oos_rate,
        int(categories or 0),
        oos_total,
    )


async def market_insights_csv_rows(
    session: AsyncSession,
    *,
    category: str | None = None,
    brand: str | None = None,
    level: Literal["district", "store"] = "district",
) -> list[dict[str, str | float | int]]:
    if level == "store":
        return await _store_export_rows(session, category=category, brand=brand)
    return await _district_export_rows(session, category=category, brand=brand)


async def _district_export_rows(
    session: AsyncSession,
    *,
    category: str | None,
    brand: str | None,
) -> list[dict[str, str | float | int]]:
    filters = [PriceEstimate.store_id.is_not(None), Product.mrp_etb.is_not(None)]
    if category:
        filters.append(Product.category == ProductCategory(category))
    if brand:
        filters.append(Product.brand.ilike(brand.strip()))

    rows = (
        await session.execute(
            select(
                Product.canonical_name,
                Product.brand,
                Product.category,
                Store.district,
                Product.mrp_etb,
                func.avg(PriceEstimate.price_etb),
                func.count(),
            )
            .join(Product, Product.id == PriceEstimate.product_id)
            .join(Store, Store.id == PriceEstimate.store_id)
            .where(*filters)
            .group_by(
                Product.canonical_name,
                Product.brand,
                Product.category,
                Store.district,
                Product.mrp_etb,
            )
            .order_by(Product.brand, Product.canonical_name, Store.district)
        )
    ).all()

    export: list[dict[str, str | float | int]] = []
    for name, brand_name, cat, district, mrp, avg_price, shops in rows:
        mrp_value = float(mrp)
        avg = float(avg_price)
        export.append(
            {
                "product": name,
                "brand": brand_name,
                "category": cat.value,
                "district": district,
                "mrp_etb": round(mrp_value, 2),
                "avg_price_etb": round(avg, 2),
                "delta_pct": round(100 * (avg - mrp_value) / mrp_value, 1),
                "band": compliance_band(avg, mrp_value),
                "shops": int(shops),
            }
        )
    return export


async def _store_export_rows(
    session: AsyncSession,
    *,
    category: str | None,
    brand: str | None,
) -> list[dict[str, str | float | int]]:
    filters = [PriceEstimate.store_id.is_not(None), Product.mrp_etb.is_not(None)]
    if category:
        filters.append(Product.category == ProductCategory(category))
    if brand:
        filters.append(Product.brand.ilike(brand.strip()))

    rows = (
        await session.execute(
            select(
                Product.canonical_name,
                Product.brand,
                Product.category,
                Store.name,
                Store.district,
                Product.mrp_etb,
                PriceEstimate.price_etb,
            )
            .join(Product, Product.id == PriceEstimate.product_id)
            .join(Store, Store.id == PriceEstimate.store_id)
            .where(*filters)
            .order_by(Product.brand, Product.canonical_name, Store.district, Store.name)
        )
    ).all()

    return [
        {
            "product": name,
            "brand": brand_name,
            "category": cat.value,
            "store": store_name,
            "district": district,
            "mrp_etb": round(float(mrp), 2),
            "price_etb": round(float(price), 2),
            "delta_pct": round(100 * (float(price) - float(mrp)) / float(mrp), 1),
            "band": compliance_band(float(price), float(mrp)),
        }
        for name, brand_name, cat, store_name, district, mrp, price in rows
    ]
