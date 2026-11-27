"""Tests for deterministic barcode decoding from photos."""

import pytest
from PIL import Image, ImageFilter

zxingcpp = pytest.importorskip("zxingcpp")

from backend.agent.barcode_decoder import _barcode_regions, decode_barcode_from_image  # noqa: E402

EAN = "5099751502913"
POSITION = (2790, 2400)


def _photo_with_barcode() -> tuple[Image.Image, tuple[int, int]]:
    """Large noisy photo with a small rotated barcode in the bottom-right corner."""
    code = zxingcpp.write_barcode(zxingcpp.BarcodeFormat.EAN13, EAN, width=190, height=80, quiet_zone=10)
    rows, cols = code.shape
    barcode = Image.frombuffer("L", (cols, rows), bytes(code)).convert("RGB")
    barcode = barcode.rotate(90, expand=True).filter(ImageFilter.GaussianBlur(0.6))
    photo = Image.effect_noise((3000, 3000), 40).convert("RGB").filter(ImageFilter.GaussianBlur(3))
    photo.paste(barcode, POSITION)
    return photo, barcode.size


def test_locator_finds_small_barcode_in_large_photo():
    photo, (width, height) = _photo_with_barcode()
    cx, cy = POSITION[0] + width // 2, POSITION[1] + height // 2

    assert any(x0 <= cx <= x1 and y0 <= cy <= y1 for x0, y0, x1, y1 in _barcode_regions(photo))


def test_decodes_small_rotated_barcode():
    photo, _ = _photo_with_barcode()

    assert decode_barcode_from_image(photo) == EAN


def test_blank_photo_has_no_barcode():
    assert decode_barcode_from_image(Image.new("RGB", (2000, 2000), "white")) is None
