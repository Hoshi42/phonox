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

from PIL import Image, ImageChops, ImageFilter, ImageOps

from backend.agent.barcode_utils import has_valid_check_digit

logger = logging.getLogger(__name__)

try:
    import zxingcpp
except ImportError:  # optional dependency: fall back to the LLM reading
    zxingcpp = None

# Photos are 3000 px+; the decoder does best on moderately sized images, sometimes upscaled
_TIME_BUDGET_SECONDS = 6.0
_MAX_SIDE = 4000
_LOCATE_SIDE = 1000  # longest side used to find the barcode
_CELL = 6  # px of the located image per grid cell
_MIN_PEAK = 12  # minimum stripe score; below this there is no barcode-like region


def _valid_digits(text: str) -> Optional[str]:
    digits = "".join(c for c in text if c.isdigit())
    if len(digits) not in (12, 13) or not has_valid_check_digit(digits):
        return None
    # EAN-13 with a leading 0 is the UPC-A number (the form Discogs lists)
    return digits[1:] if len(digits) == 13 and digits.startswith("0") else digits


def _barcode_regions(image: Image.Image, max_regions: int = 6) -> list[tuple[int, int, int, int]]:
    """Boxes (original pixel coordinates) of stripe-like regions, best first.

    Barcodes are dense in strong gradients along one axis and weak along the other,
    in either orientation. Uses PIL only.
    """
    width, height = image.size
    scale = min(1.0, _LOCATE_SIDE / max(width, height))
    gray = ImageOps.grayscale(image)
    if scale < 1.0:
        gray = gray.resize((max(1, int(width * scale)), max(1, int(height * scale))), Image.BILINEAR)
    gx = ImageChops.difference(ImageChops.offset(gray, 1, 0), ImageChops.offset(gray, -1, 0))
    gy = ImageChops.difference(ImageChops.offset(gray, 0, 1), ImageChops.offset(gray, 0, -1))

    found = []
    for strong, weak in ((gx, gy), (gy, gx)):
        score = ImageChops.subtract(strong, weak)
        score.paste(0, (0, 0, score.width, 2))  # offset() wraps around, faking edges at the border
        score.paste(0, (0, score.height - 2, score.width, score.height))
        score.paste(0, (0, 0, 2, score.height))
        score.paste(0, (score.width - 2, 0, score.width, score.height))
        score = score.filter(ImageFilter.BoxBlur(2))
        cols, rows = max(1, score.width // _CELL), max(1, score.height // _CELL)
        values = list(score.resize((cols, rows), Image.BOX).getdata())
        peak = max(values)
        if peak < _MIN_PEAK:
            continue
        hot = {(i % cols, i // cols) for i, v in enumerate(values) if v >= max(_MIN_PEAK, peak * 0.4)}
        # Close one-cell gaps so a barcode is a single blob
        hot |= {(x + dx, y + dy) for x, y in list(hot) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                if 0 <= x + dx < cols and 0 <= y + dy < rows and values[(y + dy) * cols + x + dx] >= _MIN_PEAK * 0.6}
        seen = set()
        for cell in hot:
            if cell in seen:
                continue
            blob, stack = [], [cell]
            seen.add(cell)
            while stack:
                x, y = stack.pop()
                blob.append((x, y))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nxt = (x + dx, y + dy)
                        if nxt in hot and nxt not in seen:
                            seen.add(nxt)
                            stack.append(nxt)
            if len(blob) < 4:
                continue
            xs, ys = [c[0] for c in blob], [c[1] for c in blob]
            weight = sum(values[y * cols + x] for x, y in blob)
            found.append((weight, min(xs), min(ys), max(xs) + 1, max(ys) + 1))

    boxes = []
    for _, x0, y0, x1, y1 in sorted(found, reverse=True)[:max_regions]:
        margin = max(x1 - x0, y1 - y0) * 0.3 + 1
        boxes.append((
            max(0, int((x0 - margin) * _CELL / scale)),
            max(0, int((y0 - margin) * _CELL / scale)),
            min(width, int((x1 + margin) * _CELL / scale)),
            min(height, int((y1 + margin) * _CELL / scale)),
        ))
    return boxes


def _variants(image: Image.Image) -> Iterator[Image.Image]:
    """Cheap variants first; located regions before blind tiles (barcodes are small)."""
    width, height = image.size
    longest = max(width, height)
    yield image
    if longest > 1600:
        scale = 1600 / longest
        yield image.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
    # A small, blurry barcode only decodes at the right scale, so try several
    for box in _barcode_regions(image):
        region = image.crop(box)
        for factor in (2, 1, 1.5, 3, 0.75):
            yield region.resize((max(1, int(region.width * factor)), max(1, int(region.height * factor))), Image.LANCZOS)
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
