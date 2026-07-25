"""Turn an uploaded file into bytes the ingest path is willing to read."""

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, UploadFile, status

from app.schemas.common import ErrorResponse

ALLOWED_MIME_TYPES = ("image/jpeg", "image/png", "image/webp")
MAX_UPLOAD_BYTES = 8 * 1024 * 1024

UPLOAD_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_413_CONTENT_TOO_LARGE: {
        "model": ErrorResponse,
        "description": "The image is larger than 8MB.",
    },
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {
        "model": ErrorResponse,
        "description": f"The image must be one of {', '.join(ALLOWED_MIME_TYPES)}.",
    },
    status.HTTP_502_BAD_GATEWAY: {
        "model": ErrorResponse,
        "description": "The image could not be read; ask the shopper to retake it.",
    },
}


@dataclass(frozen=True, slots=True)
class Image:
    data: bytes
    mime_type: str


async def read_image(upload: UploadFile) -> Image:
    mime_type = (upload.content_type or "").split(";")[0].strip().casefold()
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Upload a {', '.join(ALLOWED_MIME_TYPES)} image, not {mime_type or 'nothing'}.",
        )

    data = await upload.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Images must be under 8MB; photograph the receipt rather than scanning it.",
        )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded image was empty.",
        )
    return Image(data=data, mime_type=mime_type)
