"""The ingestion log: every price anyone submitted and what the gate did with it."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EvidenceStatus
from app.models.evidence import Evidence
from app.models.product import Product
from app.models.store import Store
from app.repositories.mappers import as_utc
from app.schemas.evidence import EvidenceLogItem, EvidenceLogResponse


async def load_evidence_log(
    session: AsyncSession,
    *,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> EvidenceLogResponse:
    statement = (
        select(Evidence, Product.canonical_name, Store.name)
        .join(Product, Product.id == Evidence.product_id)
        .outerjoin(Store, Store.id == Evidence.store_id)
    )
    if status:
        statement = statement.where(Evidence.status == EvidenceStatus(status))

    total = await session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = (
        await session.execute(
            statement.order_by(Evidence.created_at.desc()).limit(limit).offset(offset)
        )
    ).all()

    return EvidenceLogResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[
            EvidenceLogItem(
                id=evidence.id,
                product_name=product_name,
                store_name=store_name,
                price_etb=float(evidence.price_etb),
                source_type=evidence.source_type.value,
                status=evidence.status.value,
                rejection_reason=evidence.rejection_reason,
                observed_at=as_utc(evidence.observed_at),
                created_at=as_utc(evidence.created_at),
            )
            for evidence, product_name, store_name in rows
        ],
    )
