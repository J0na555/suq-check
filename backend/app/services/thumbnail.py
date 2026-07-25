"""Shrink an upload to something worth keeping next to the evidence row.

The design deliberately does not store original images: a small JPEG in `bytea`
gives the audit trail without object storage, signed URLs, or another service to
deploy. Anything that cannot be shrunk is simply not kept.
"""

from io import BytesIO

MAX_BYTES = 64 * 1024
MAX_EDGE = 320
QUALITY_LADDER = (80, 65, 50, 35)


def of(image: bytes) -> bytes | None:
    """A JPEG under 64KB, or None when one cannot be produced."""
    try:
        from PIL import Image, UnidentifiedImageError
    except ModuleNotFoundError:  # pragma: no cover - deployment dependency
        # The thumbnail is an audit nicety; ingestion still works without it.
        return None

    try:
        with Image.open(BytesIO(image)) as opened:
            frame = opened.convert("RGB")
            frame.thumbnail((MAX_EDGE, MAX_EDGE))
            for quality in QUALITY_LADDER:
                buffer = BytesIO()
                frame.save(buffer, format="JPEG", quality=quality, optimize=True)
                if buffer.tell() <= MAX_BYTES:
                    return buffer.getvalue()
    except (UnidentifiedImageError, OSError, ValueError):
        return None
    return None
