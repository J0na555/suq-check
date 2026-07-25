"""Thumbnails, which only exist so an evidence row has something to show."""

from io import BytesIO

import pytest

from app.services import thumbnail

Image = pytest.importorskip("PIL.Image", reason="Pillow is a deployment dependency")


def photo(width: int, height: int) -> bytes:
    frame = Image.new("RGB", (width, height))
    for x in range(width):
        for y in range(0, height, 7):
            frame.putpixel((x, y), ((x * 7) % 256, (y * 13) % 256, (x + y) % 256))

    buffer = BytesIO()
    frame.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


def test_a_camera_sized_photo_is_shrunk_under_the_limit() -> None:
    original = photo(2048, 1536)
    assert len(original) > thumbnail.MAX_BYTES

    small = thumbnail.of(original)

    assert small is not None
    assert len(small) <= thumbnail.MAX_BYTES
    with Image.open(BytesIO(small)) as opened:
        assert opened.format == "JPEG"
        assert max(opened.size) <= thumbnail.MAX_EDGE


def test_a_small_photo_survives_intact() -> None:
    small = thumbnail.of(photo(200, 150))

    assert small is not None
    with Image.open(BytesIO(small)) as opened:
        assert opened.size == (200, 150)


def test_something_that_is_not_an_image_is_simply_not_kept() -> None:
    assert thumbnail.of(b"this is not a photograph") is None
    assert thumbnail.of(b"") is None
