"""Per-device and per-IP limits on the write endpoints.

Anonymous uploads cost a Gemini call and can move a price, so they are capped.
Combined with the low source weight community reports carry, one device cannot
meaningfully shift an estimate no matter how many times it submits.

The counters live in this process. One free Render instance serves the demo, so
a shared store would be infrastructure with nothing to show for it.
"""

from collections import defaultdict, deque
from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True, slots=True)
class Limit:
    requests: int
    per_seconds: float

    def __str__(self) -> str:
        minutes = round(self.per_seconds / 60)
        return f"{self.requests} uploads every {minutes} minutes"


DEVICE_LIMIT = Limit(requests=30, per_seconds=600)
ADDRESS_LIMIT = Limit(requests=90, per_seconds=600)


class SlidingWindow:
    """Counts recent hits per key and says how long to wait after the cap."""

    def __init__(self, limit: Limit) -> None:
        self.limit = limit
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, *, at: float | None = None) -> float | None:
        """Record a request, or return the seconds to wait if it is over the cap."""
        now = monotonic() if at is None else at
        recent = self._hits[key]
        while recent and recent[0] <= now - self.limit.per_seconds:
            recent.popleft()

        if len(recent) >= self.limit.requests:
            return max(recent[0] + self.limit.per_seconds - now, 1.0)

        recent.append(now)
        return None

    def clear(self) -> None:
        self._hits.clear()


_by_device = SlidingWindow(DEVICE_LIMIT)
_by_address = SlidingWindow(ADDRESS_LIMIT)


@dataclass(frozen=True, slots=True)
class Rejection:
    retry_after_seconds: int
    limit: Limit

    @property
    def detail(self) -> str:
        return (
            f"Too many uploads from this {'device' if self.limit is DEVICE_LIMIT else 'network'}. "
            f"The limit is {self.limit}. Try again in {self.retry_after_seconds} seconds."
        )


def check(*, device_id: str | None, address: str) -> Rejection | None:
    """Charge one upload against both windows; None means it is allowed."""
    if device_id:
        wait = _by_device.hit(device_id)
        if wait is not None:
            return Rejection(retry_after_seconds=round(wait), limit=DEVICE_LIMIT)

    wait = _by_address.hit(address)
    if wait is not None:
        return Rejection(retry_after_seconds=round(wait), limit=ADDRESS_LIMIT)
    return None


def reset() -> None:
    _by_device.clear()
    _by_address.clear()
