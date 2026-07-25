"""What routes ask for: a database session, or None while fixtures are on."""

from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import session_scope
from app.schemas.common import ErrorResponse
from app.services import rate_limit

RATE_LIMIT_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_429_TOO_MANY_REQUESTS: {
        "model": ErrorResponse,
        "description": (
            "The per-device or per-network upload limit was reached. "
            "The `Retry-After` header carries the wait in seconds."
        ),
    },
}

DeviceIdHeader = Annotated[
    str | None,
    Header(alias="X-Device-Id", description="Anonymous device identifier used for rate limiting."),
]


async def optional_session() -> AsyncIterator[AsyncSession | None]:
    """None means `USE_FIXTURES` is on, so the route answers from `contracts/`.

    Yielding None rather than opening a session keeps the deployed stub working
    with no database attached at all.
    """
    if get_settings().use_fixtures:
        yield None
        return

    async with session_scope() as session:
        yield session


def client_ip(request: Request) -> str:
    """The caller's address, trusting Render's proxy header when present."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_upload_limit(
    address: Annotated[str, Depends(client_ip)],
    device_id: DeviceIdHeader = None,
) -> None:
    rejection = rate_limit.check(device_id=device_id, address=address)
    if rejection is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=rejection.detail,
            headers={"Retry-After": str(rejection.retry_after_seconds)},
        )


SessionDep = Annotated[AsyncSession | None, Depends(optional_session)]
RateLimited = Depends(enforce_upload_limit)
