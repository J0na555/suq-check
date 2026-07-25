from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import get_settings


def async_database_url(value: str) -> URL:
    if not value:
        raise RuntimeError("DATABASE_URL is required when fixture mode is disabled")

    url = make_url(value)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+asyncpg")

    if url.drivername == "postgresql+asyncpg":
        query = dict(url.query)
        if "sslmode" in query:
            query["ssl"] = query.pop("sslmode")
        # asyncpg does not expose libpq's channel_binding URL option.
        query.pop("channel_binding", None)
        url = url.set(query=query)

    return url


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    url = async_database_url(settings.database_url)
    is_neon_pooler = "-pooler." in (url.host or "")
    is_sqlite = url.drivername.startswith("sqlite")

    options: dict[str, object] = {
        "echo": settings.database_echo,
        "pool_pre_ping": not is_neon_pooler,
    }
    if is_neon_pooler:
        # Neon already pools these connections with PgBouncer. NullPool avoids
        # stacking a second client-side pool on top.
        options["poolclass"] = NullPool
        options["connect_args"] = {"statement_cache_size": 0}
    elif not is_sqlite:
        options["pool_size"] = settings.database_pool_size

    return create_async_engine(url, **options)


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """One session, rolled back if the caller raises. Committing is the caller's job."""
    async with get_session_factory()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with session_scope() as session:
        yield session


async def close_database() -> None:
    if not get_settings().database_url:
        return
    await get_engine().dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()

