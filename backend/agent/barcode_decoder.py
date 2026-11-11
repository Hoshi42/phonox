"""
Deterministic UPC/EAN decoding from record photos.

Reading digits with a vision LLM is unreliable (misread or invented digits), so the
barcode is first decoded from the bars themselves. Only results with a valid check
digit are returned.
"""

import base64
import io
import logging
import time
from typing import Iterator, Optional

from PIL import Image, ImageOps

from backend.agent.barcode_utils import has_valid_check_digit

logger = logging.getLogger(__name__)

try:
    import zxingcpp
except ImportError:  # optional dependency: fall back to the LLM reading
    zxingcpp = None

# Photos are 3000 px+; the decoder does best on moderately sized images, sometimes upscaled
_TIME_BUDGET_SECONDS = 6.0
_MAX_SIDE = 4000


def _valid_digits(text: str) -> Optional[str]:
    digits = "".join(c for c in text if c.isdigit())
    if len(digits) not in (12, 13) or not has_valid_check_digit(digits):
        return None
    # EAN-13 with a leading 0 is the UPC-A number (the form Discogs lists)
    return digits[1:] if len(digits) == 13 and digits.startswith("0") else digits


def _variants(image: Image.Image) -> Iterator[Image.Image]:
    """Cheap variants first; tiles of the image last (barcodes are small)."""
    width, height = image.size
    longest = max(width, height)
    yield image
    if longest > 1600:
        scale = 1600 / longest
        yield image.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
    if longest * 2 <= _MAX_SIDE:
        yield image.resize((width * 2, height * 2), Image.LANCZOS)
    steps = 3
    for i in range(steps):
        for j in range(steps):
            left, top = int(i * width / steps * 0.85), int(j * height / steps * 0.85)
            yield image.crop((left, top, min(width, left + int(width / steps * 1.3)), min(height, top + int(height / steps * 1.3))))


def decode_barcode_from_image(image: Image.Image) -> Optional[str]:
    """Decode a UPC/EAN barcode with a valid check digit from a PIL image, or None."""
    if zxingcpp is None:
        return None
    started = time.monotonic()
    for variant in _variants(image):
        if time.monotonic() - started > _TIME_BUDGET_SECONDS:
            break
        for candidate in (variant, ImageOps.autocontrast(variant.convert("L"))):
            for result in zxingcpp.read_barcodes(candidate, try_rotate=True, try_downscale=True, try_invert=True):
                digits = _valid_digits(result.text)
                if digits:
                    return digits
    return None


def decode_barcode(image_base64: str) -> Optional[str]:
    """Decode a barcode from a base64 encoded photo. Never raises."""
    try:
        image = Image.open(io.BytesIO(base64.b64decode(image_base64)))
        image = ImageOps.exif_transpose(image).convert("RGB")
        return decode_barcode_from_image(image)
    except Exception as e:
        logger.warning(f"Barcode decoding failed: {e}")
        return None
