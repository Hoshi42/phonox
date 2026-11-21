"""Landscape A4 collector's catalogue: compact album and artist cards, up to six albums per page.

Colours follow the Phonox app (warm paper, near-black ink, one red accent). Typefaces are IBM Plex
(SIL Open Font License, see backend/fonts/OFL.txt): Sans Condensed for headings, Serif for text and
Mono for catalogue data. Missing information is simply left out; the layout never mentions what is unknown.
"""

import unicodedata
from collections import Counter
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from PIL import Image as PillowImage, ImageOps
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, FrameBreak, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer,
)
from reportlab.platypus.tableofcontents import TableOfContents

from backend.magazine_models import MagazineArtist, MagazineDraft, MagazineImage, MagazineRecord, MagazineSource
from backend.magazine_service import artist_name, asset_path, record_order

PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)
MARGIN_X = 12 * mm
MARGIN_TOP = 18 * mm
MARGIN_BOTTOM = 18 * mm
GUTTER = 8 * mm
FRAME_HEIGHT = PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM
CELL_WIDTH = (PAGE_WIDTH - 2 * MARGIN_X - GUTTER) / 2
TEXT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X
TOP_GAP = 3 * mm
BOTTOM_GAP = 1 * mm
HEADER_HEIGHT = 4 * mm
CARD_GAP = 3 * mm
ROW_HEIGHT = 4.6 * mm
SPINE_WIDTH = 16 * mm
COVER_SIZE = 32 * mm
THUMB_SIZE = (COVER_SIZE - 2 * mm) / 2
TEXT_MAX_HEIGHT = 52 * mm
MAX_IMAGES = 3
PORTRAIT_MAX_HEIGHT = 46 * mm
IMAGE_DPI = 140  # cards show photos at 15–32 mm; more resolution only inflates the file
IMAGE_QUALITY = 68
COVER_DPI = 120

# The palette of frontend/src/styles/tokens.css (light theme)
INK = colors.HexColor("#16161a")
MUTED = colors.HexColor("#62626b")
ACCENT = colors.HexColor("#d93a2b")
PAPER = colors.HexColor("#f5f4f0")
RULE = colors.HexColor("#d9d8d3")
TINT = colors.HexColor("#eceae4")
WHITE = colors.white

FONT_DIRECTORY = Path(__file__).parent / "fonts"
FONT_FILES = {
    "MagazineBody": "IBMPlexSerif-Regular.ttf",
    "MagazineItalic": "IBMPlexSerif-Italic.ttf",
    "MagazineBold": "IBMPlexSerif-Bold.ttf",
    "MagazineCond": "IBMPlexSansCondensed-Bold.ttf",
    "MagazineMono": "IBMPlexMono-Regular.ttf",
    "MagazineMonoMed": "IBMPlexMono-Medium.ttf",
    "MagazineMonoSemi": "IBMPlexMono-SemiBold.ttf",
}


def register_fonts() -> None:
    for name, filename in FONT_FILES.items():
        if name not in pdfmetrics.getRegisteredFontNames():
            path = FONT_DIRECTORY / filename
            if not path.is_file():
                raise RuntimeError(f"Magazine font missing: {path}. Rebuild the backend image.")
            pdfmetrics.registerFont(TTFont(name, str(path)))
    pdfmetrics.registerFontFamily("MagazineBody", normal="MagazineBody", bold="MagazineBold",
                                  italic="MagazineItalic", boldItalic="MagazineBold")


def fit_mono(text: str, font: str, size: float, space: float, width: float) -> str:
    """Upper-case catalogue text, shortened with an ellipsis when it would overflow `width`."""
    text = " ".join(text.upper().split())

    def measure(value: str) -> float:
        return pdfmetrics.stringWidth(value, font, size) + space * max(len(value) - 1, 0)

    if measure(text) <= width:
        return text
    while text and measure(text + "…") > width:
        text = text[:-1]
    return text.rstrip() + "…"


def draw_mono(canvas, x: float, y: float, text: str, size: float = 6.5, color=MUTED, space: float = 0.7,
              align: str = "l", font: str = "MagazineMono", width: float | None = None) -> None:
    """Tracked upper-case label. Character spacing is part of the PDF graphics state, so it is reset afterwards."""
    text = fit_mono(text, font, size, space, width) if width else text.upper()
    span = pdfmetrics.stringWidth(text, font, size) + space * max(len(text) - 1, 0)
    line = canvas.beginText()
    line.setTextOrigin(x - (span if align == "r" else span / 2 if align == "c" else 0), y)
    line.setFont(font, size)
    line.setCharSpace(space)
    line.setFillColor(color)
    line.textOut(text)
    line.setCharSpace(0)
    canvas.drawText(line)


def draw_roundel(canvas, cx: float, cy: float, radius: float, edition: int, disc=INK, ink=WHITE) -> None:
    """Label stamp with the edition number, after the circle-and-number marks of record labels."""
    canvas.setFillColor(disc)
    canvas.circle(cx, cy, radius, stroke=0, fill=1)
    draw_mono(canvas, cx, cy + radius * 0.28, "Phonox", max(4.5, min(8, radius * 0.045)), ink, 1.2, "c", "MagazineMonoMed")
    canvas.setFillColor(ink)
    canvas.setFont("MagazineCond", radius * 0.62)
    canvas.drawCentredString(cx, cy - radius * 0.38, f"№{edition:03d}")


def style(name: str, font: str = "MagazineBody", size: float = 9, leading: float | None = None,
          color=INK, after: float = 0) -> ParagraphStyle:
    return ParagraphStyle(name, fontName=font, fontSize=size, leading=leading or size * 1.32,
                          textColor=color, spaceAfter=after)


def block(text: str, paragraph_style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text).replace("\n", "<br/>"), paragraph_style)


def paragraphs(text: str, paragraph_style: ParagraphStyle) -> list[Flowable]:
    return [block(part.strip(), paragraph_style) for part in text.split("\n\n") if part.strip()]


class SectionHeading(Paragraph):
    """Heading that registers a PDF bookmark and, optionally, a contents entry."""

    def __init__(self, text: str, paragraph_style: ParagraphStyle, key: str, level: int, contents: bool = False):
        super().__init__(escape(text), paragraph_style)
        self.entries = [(level, text, key)]
        self.contents = contents


class MagazineDocument(BaseDocTemplate):
    def __init__(self, filename: str, draft: MagazineDraft, check: Callable[[], None], edition: int = 1):
        super().__init__(filename, pagesize=landscape(A4), leftMargin=MARGIN_X, rightMargin=MARGIN_X,
                         topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM,
                         title=draft.settings.title, author=draft.settings.display_name or "Phonox")
        self.check = check
        self.magazine_title = draft.settings.title
        self.edition, self.dated = edition, draft.snapshot_at[:10]
        self.on_page: Callable[[int], None] | None = None
        # The contents need several passes anyway; the page count of the previous pass is the total of the next.
        self.seen_pages = self.total_pages = 0

        def frame(x: float, width: float, frame_id: str) -> Frame:
            return Frame(x, MARGIN_BOTTOM, width, FRAME_HEIGHT, id=frame_id,
                         leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

        column = (TEXT_WIDTH - GUTTER) / 2
        self.addPageTemplates([
            PageTemplate(id="cover", frames=[Frame(0, 0, PAGE_WIDTH, PAGE_HEIGHT - 0.5, id="cover",
                                                   leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)],
                         onPage=self.draw_cover_page),
            PageTemplate(id="columns", frames=[frame(MARGIN_X, column, "left"),
                                               frame(MARGIN_X + column + GUTTER, column, "right")],
                         onPage=self.draw_page),
            PageTemplate(id="cells", frames=[frame(MARGIN_X, CELL_WIDTH, "cell-left"),
                                             frame(MARGIN_X + CELL_WIDTH + GUTTER, CELL_WIDTH, "cell-right")],
                         onPage=self.draw_page),
        ])

    def beforeDocument(self):
        self.total_pages, self.seen_pages = self.seen_pages, 0

    def afterPage(self):
        self.seen_pages = max(self.seen_pages, self.page)

    def draw_cover_page(self, canvas, doc):
        self.check()
        canvas.setFillColor(ACCENT)
        canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)

    def draw_page(self, canvas, doc):
        self.check()
        if self.on_page:
            self.on_page(doc.page)
        canvas.setFillColor(PAPER)
        canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)
        right = PAGE_WIDTH - MARGIN_X
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.25)
        canvas.line(MARGIN_X, PAGE_HEIGHT - 13 * mm, right, PAGE_HEIGHT - 13 * mm)
        canvas.line(MARGIN_X, 15 * mm, right, 15 * mm)
        stamp = f"Collection № {self.edition:03d} · {self.dated}"
        stamp_width = pdfmetrics.stringWidth(stamp, "MagazineMono", 6.5) + 0.9 * len(stamp)
        draw_mono(canvas, MARGIN_X, PAGE_HEIGHT - 10 * mm, self.magazine_title, 6.5, INK, 0.9, "l",
                  "MagazineMonoMed", width=TEXT_WIDTH - stamp_width - 10 * mm)
        draw_mono(canvas, right, PAGE_HEIGHT - 10 * mm, stamp, 6.5, MUTED, 0.9, "r")
        canvas.setFillColor(ACCENT)
        canvas.setFont("MagazineMonoSemi", 14)
        folio = f"{doc.page:03d}"
        canvas.drawString(MARGIN_X, 7.5 * mm, folio)
        if self.total_pages:
            draw_mono(canvas, MARGIN_X + canvas.stringWidth(folio, "MagazineMonoSemi", 14) + 1.5 * mm, 7.9 * mm,
                      f"/ {self.total_pages:03d}", 6.5, MUTED, 0.7)
        draw_mono(canvas, right, 7.9 * mm, "Phonox · The Collection Edition", 6, MUTED, 0.9, "r")

    def afterFlowable(self, flowable):
        for level, title, key in getattr(flowable, "entries", []):
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, level=level, closed=False)
            if getattr(flowable, "contents", False):
                self.notify("TOCEntry", (level, escape(title), self.page, key))


_IMAGE_CACHE: dict[tuple, tuple[bytes, float, float]] = {}


def embedded(path: Path, width: float, height: float, crop: bool, dpi: int = IMAGE_DPI,
             quality: int = IMAGE_QUALITY) -> tuple[ImageReader, float, float]:
    """Image resampled to what the printed size needs, so the PDF stays small.

    The result is cached because the document is typeset in several passes.
    """
    key = (str(path), round(width, 1), round(height, 1), crop, dpi, quality)
    if key not in _IMAGE_CACHE:
        with PillowImage.open(path) as source:
            photo = source.convert("RGB")
        if crop:
            draw_w, draw_h = width, height
            scale = min(1.0, photo.width / (width / 72 * dpi), photo.height / (height / 72 * dpi))
            target = (max(1, int(width / 72 * dpi * scale)), max(1, int(height / 72 * dpi * scale)))
            photo = ImageOps.fit(photo, target, method=PillowImage.Resampling.LANCZOS)
        else:
            ratio = min(width / photo.width, height / photo.height)
            draw_w, draw_h = photo.width * ratio, photo.height * ratio
            target = (max(1, int(draw_w / 72 * dpi)), max(1, int(draw_h / 72 * dpi)))
            if target[0] < photo.width:
                photo = photo.resize(target, PillowImage.Resampling.LANCZOS)
        data = BytesIO()
        photo.save(data, "JPEG", quality=quality, optimize=True)
        _IMAGE_CACHE[key] = (data.getvalue(), draw_w, draw_h)
    content, draw_w, draw_h = _IMAGE_CACHE[key]
    return ImageReader(BytesIO(content)), draw_w, draw_h


def draw_image(canvas, magazine_id: str, image: MagazineImage, x: float, y: float, width: float,
               height: float, crop: bool = False, backdrop=TINT) -> None:
    assert image.asset is not None
    canvas.setFillColor(backdrop)
    canvas.rect(x, y, width, height, stroke=0, fill=1)
    reader, draw_w, draw_h = embedded(asset_path(magazine_id, image.asset), width, height, crop)
    canvas.drawImage(reader, x + (width - draw_w) / 2, y + (height - draw_h) / 2, draw_w, draw_h)


def fit_text(text: str, width: float, max_height: float, color=INK, sizes=(9.5, 9, 8.5, 8, 7.5),
             font: str = "MagazineBody") -> tuple[list[Paragraph], bool]:
    """Largest size that fits; as a last resort the text is cut at a word boundary."""
    parts = [part.strip() for part in text.split("\n\n") if part.strip()]
    if not parts:
        return [], False

    def build(blocks: list[str], size: float) -> tuple[list[Paragraph], float]:
        styled = style(f"fit-{size}", font, size, color=color, after=size * 0.4)
        result = [block(part, styled) for part in blocks]
        total = sum(item.wrap(width, 10_000)[1] + styled.spaceAfter for item in result)
        return result, total

    for size in sizes:
        result, total = build(parts, size)
        if total <= max_height:
            return result, False
    words = " ".join(parts).split()
    low, high = 0, len(words)
    while low < high:
        middle = (low + high + 1) // 2
        _, total = build([" ".join(words[:middle]) + " …"], sizes[-1])
        if total <= max_height:
            low = middle
        else:
            high = middle - 1
    result, _ = build([" ".join(words[:low]) + " …"], sizes[-1])
    return result, True


def draw_paragraphs(canvas, items: list[Paragraph], x: float, top: float) -> float:
    for item in items:
        top -= item.height
        item.drawOn(canvas, x, top)
        top -= item.style.spaceAfter
    return top


def stacked_height(items: list[Paragraph]) -> float:
    return sum(item.height + item.style.spaceAfter for item in items)


class Card(Flowable):
    """One half page wide; its height depends on the content. A rule opens each card."""

    def __init__(self, height: float, entries: list[tuple[int, str, str]]):
        super().__init__()
        self.width, self.height = CELL_WIDTH, height
        self.entries = entries
        self.contents = False
        self.spaceAfter = CARD_GAP
        self.warnings: list[str] = []

    def draw_rule(self, heavy: bool = False) -> None:
        canvas = self.canv
        canvas.setStrokeColor(INK if heavy else RULE)
        canvas.setLineWidth(0.9 if heavy else 0.25)
        canvas.line(0, self.height, self.width, self.height)


class LetterMarker(Flowable):
    """Invisible anchor in front of the first artist of each initial; the contents list these letters."""

    def __init__(self, letter: str, key: str):
        super().__init__()
        self.width = self.height = 0
        self.entries = [(0, letter, key)]
        self.contents = True
        self.keepWithNext = True
        self.warnings: list[str] = []

    def draw(self):
        pass


def initial(name: str) -> str:
    letter = unicodedata.normalize("NFKD", name.strip()[:1]).encode("ascii", "ignore").decode().upper()
    return letter if letter.isalpha() else "#"


class AlbumCard(Card):
    """Cover and photographs on the left; plate number, title and a catalogue data sheet on the right."""

    def __init__(self, record: MagazineRecord, title: str, magazine_id: str, include_notes: bool,
                 entries: list[tuple[int, str, str]], number: int):
        super().__init__(0, entries)
        self.record, self.title, self.magazine_id, self.include_notes = record, title, magazine_id, include_notes
        self.number = number
        self.images = [image for image in record.images if image.asset][:MAX_IMAGES]
        self.text_x = COVER_SIZE + 5 * mm if self.images else 0
        self.text_w = self.width - self.text_x
        self.rows = self.data_rows()
        self.head: list[Paragraph] = []
        self.body: list[Paragraph] = []
        self.layout()

    def data_rows(self) -> list[list[tuple[str, str]]]:
        record = self.record
        value = f"EUR {record.value_eur:,.0f}" if record.value_eur is not None else ""
        rows = [[("Cat. no", record.catalog_number), ("Label", record.label)],
                [("Year", str(record.year) if record.year else ""), ("Grade", record.condition), ("Value", value)]]
        cleaned = [[(key, value.strip()) for key, value in row if value and value.strip()] for row in rows]
        return [row for row in cleaned if row]

    def layout(self) -> None:
        """Paragraphs and height; the card is as tall as the photographs or the text, whichever is taller."""
        record, text_w = self.record, self.text_w
        for size in (13, 12, 11, 10):
            heading = block(self.title, style("album-title", "MagazineCond", size, size * 1.1, after=1.2 * mm))
            if heading.wrap(text_w, 100)[1] <= size * 1.1 * 2 + 0.1:
                break
        self.head = [heading]
        if record.artist and artist_name(record.artist).casefold() != record.group.casefold():
            self.head.append(block(record.artist.upper(), style("kicker", "MagazineMonoMed", 6.5, color=INK, after=1 * mm)))
        for item in self.head:
            item.wrap(text_w, 100)
        used = HEADER_HEIGHT + stacked_height(self.head) + len(self.rows) * ROW_HEIGHT + 1.5 * mm
        photos = (COVER_SIZE + (2 * mm + THUMB_SIZE if len(self.images) > 1 else 0)) if self.images else 0
        limit = max(photos, TEXT_MAX_HEIGHT)
        notes = record.notes if self.include_notes and record.notes else ""
        text = "\n\n".join(part for part in (record.description.strip(), notes.strip()) if part)
        if text:
            self.body, truncated = fit_text(text, text_w, limit - used, sizes=(8, 7.5, 7, 6.5))
            if truncated:
                self.warnings.append(f"Text shortened to fit its card: {self.title}.")
            used += stacked_height(self.body)
        trailing = (self.body or self.head)[-1].style.spaceAfter
        self.height = TOP_GAP + BOTTOM_GAP + max(photos, used - trailing)

    def draw_row(self, row: list[tuple[str, str]], x: float, top: float) -> None:
        canvas, gap = self.canv, 3 * mm
        cell = (self.text_w - gap * (len(row) - 1)) / len(row)
        baseline = top - 3.1 * mm
        for index, (key, value) in enumerate(row):
            left = x + index * (cell + gap)
            draw_mono(canvas, left, baseline, key, 5.4, MUTED, 0.7)
            key_width = pdfmetrics.stringWidth(key.upper(), "MagazineMono", 5.4) + 0.7 * len(key) + 2 * mm
            font, size, color = ("MagazineMonoSemi", 7.6, ACCENT) if key == "Value" else ("MagazineMonoMed", 6.4, INK)
            draw_mono(canvas, left + cell, baseline, value, size, color, 0.3, "r", font, width=cell - key_width)
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.25)
        canvas.line(x, top - ROW_HEIGHT + 0.6 * mm, x + self.text_w, top - ROW_HEIGHT + 0.6 * mm)

    def draw(self):
        self.draw_rule()
        canvas = self.canv
        top = self.height - TOP_GAP
        if self.images:
            draw_image(canvas, self.magazine_id, self.images[0], 0, top - COVER_SIZE, COVER_SIZE, COVER_SIZE)
            for index, image in enumerate(self.images[1:]):
                draw_image(canvas, self.magazine_id, image, index * (THUMB_SIZE + 2 * mm),
                           top - COVER_SIZE - 2 * mm - THUMB_SIZE, THUMB_SIZE, THUMB_SIZE)
        x = self.text_x
        draw_mono(canvas, x, top - 2.6 * mm, f"PHX-{self.number:04d}", 6.5, ACCENT, 1.0, font="MagazineMonoSemi")
        genres = ", ".join(self.record.genres)
        if genres:
            draw_mono(canvas, self.width, top - 2.6 * mm, genres, 6, MUTED, 0.9, "r", width=self.text_w - 24 * mm)
        y = draw_paragraphs(canvas, self.head, x, top - HEADER_HEIGHT)
        for row in self.rows:
            self.draw_row(row, x, y)
            y -= ROW_HEIGHT
        draw_paragraphs(canvas, self.body, x, y - 1.5 * mm)


class ArtistCard(Card):
    """Chapter opener: artist name, one-line facts and portrait; its height follows the text."""

    def __init__(self, artist: MagazineArtist, entries: list[tuple[int, str, str]], chapter: int, records: int):
        super().__init__(0, entries)
        self.artist, self.chapter, self.records = artist, chapter, records
        self.keepWithNext = True
        for size in (20, 18, 16, 14):
            heading = block(artist.name, style("artist-name", "MagazineCond", size, size * 1.1, after=1.5 * mm))
            if heading.wrap(self.width, 100)[1] <= size * 1.1 * 2 + 0.1:
                break
        self.items: list[Paragraph] = [heading]
        if artist.facts.strip():
            facts = block(artist.facts.strip(), style("artist-facts", "MagazineMonoMed", 7, color=ACCENT, after=1.5 * mm))
            facts.wrap(self.width, 40)
            self.items.append(facts)
        used = HEADER_HEIGHT + stacked_height(self.items)
        if artist.portrait.strip():
            portrait, truncated = fit_text(artist.portrait, self.width,
                                           PORTRAIT_MAX_HEIGHT - TOP_GAP - BOTTOM_GAP - used, sizes=(8.5, 8, 7.5))
            if truncated:
                self.warnings.append(f"Portrait shortened to fit its card: {artist.name}.")
            self.items.extend(portrait)
        self.height = TOP_GAP + BOTTOM_GAP + HEADER_HEIGHT + stacked_height(self.items) - self.items[-1].style.spaceAfter

    def draw(self):
        self.draw_rule(heavy=True)
        canvas, top = self.canv, self.height - TOP_GAP
        draw_mono(canvas, 0, top - 2.6 * mm, f"Chapter {self.chapter:02d}", 6.5, ACCENT, 1.0, font="MagazineMonoSemi")
        draw_mono(canvas, self.width, top - 2.6 * mm, f"{self.records} {'record' if self.records == 1 else 'records'}",
                  6, MUTED, 0.9, "r")
        draw_paragraphs(canvas, self.items, 0, top - HEADER_HEIGHT)


class CoverPage(Flowable):
    """Label-livery cover: full accent colour, black spine strip, edition roundel or the chosen photograph."""

    def __init__(self, path: Path | None, draft: MagazineDraft, edition: int):
        super().__init__()
        self.width, self.height = PAGE_WIDTH, PAGE_HEIGHT - 0.5
        self.path, self.draft, self.edition = path, draft, edition

    def draw(self):
        canvas, settings = self.canv, self.draft.settings
        records, dated = len(self.draft.records), self.draft.snapshot_at[:10]
        left, width, right = SPINE_WIDTH + 14 * mm, 151 * mm, PAGE_WIDTH - MARGIN_X
        canvas.setFillColor(INK)
        canvas.rect(0, 0, SPINE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)
        canvas.saveState()
        canvas.translate(11 * mm, 12 * mm)
        canvas.rotate(90)
        draw_mono(canvas, 0, 0, f"Phonox · Collection № {self.edition:03d} · {dated[:4]}", 6.5, WHITE, 1.4)
        canvas.restoreState()
        draw_mono(canvas, left, PAGE_HEIGHT - 18 * mm, "Collector's catalogue", 7, INK, 1.4, font="MagazineMonoSemi")
        for size in (56, 46, 38, 30, 24):
            heading = Paragraph(escape(settings.title.upper()), ParagraphStyle(
                "cover-title", fontName="MagazineCond", fontSize=size, leading=size * 1.06, textColor=WHITE))
            _, h = heading.wrap(width, 100 * mm)
            if h <= 62 * mm:
                break
        top = 118 * mm
        heading.drawOn(canvas, left, top - h)
        y = top - h - 7 * mm
        canvas.setFillColor(INK)
        canvas.rect(left, y, 28 * mm, 2.2 * mm, stroke=0, fill=1)
        if settings.subtitle.strip():
            sub = Paragraph(escape(settings.subtitle.strip()), ParagraphStyle(
                "cover-sub", fontName="MagazineItalic", fontSize=13, leading=17, textColor=WHITE))
            _, sub_h = sub.wrap(width * 0.8, 40 * mm)
            sub.drawOn(canvas, left, y - 5 * mm - sub_h)
        facts = (f"{records} {'record' if records == 1 else 'records'}", settings.display_name.strip(), dated)
        draw_mono(canvas, left, 24 * mm, " · ".join(part for part in facts if part), 6.5, INK, 1.0, width=width)
        draw_mono(canvas, left, 19 * mm, f"Edition № {self.edition:03d}", 6.5, INK, 1.0, font="MagazineMonoMed")
        draw_mono(canvas, right, 14 * mm, f"PHX-0001 — PHX-{records:04d}", 6.5, INK, 1.0, "r", "MagazineMonoMed")
        if self.path:
            size = 96 * mm
            x0, y0 = right - size, (PAGE_HEIGHT - size) / 2 + 6 * mm
            reader, draw_w, draw_h = embedded(self.path, size, size, True, COVER_DPI, IMAGE_QUALITY + 2)
            canvas.drawImage(reader, x0, y0, draw_w, draw_h)
            draw_roundel(canvas, x0, y0, 17 * mm, self.edition)
        else:
            draw_roundel(canvas, PAGE_WIDTH - 62 * mm, PAGE_HEIGHT / 2 + 6 * mm, 46 * mm, self.edition)


class Colophon(Flowable):
    """Closing page element: the facts of this edition as a catalogue sheet with the edition stamp."""

    def __init__(self, rows: list[tuple[str, str]], edition: int, width: float):
        super().__init__()
        self.rows, self.edition, self.width = rows, edition, width
        self.height = max(len(rows) * 6.5 * mm, 32 * mm)
        self.warnings: list[str] = []

    def draw(self):
        canvas, y = self.canv, self.height
        for key, value in self.rows:
            draw_mono(canvas, 0, y - 3.4 * mm, key, 6, MUTED, 1.0)
            draw_mono(canvas, 28 * mm, y - 3.4 * mm, value, 6.8, INK, 0.5, font="MagazineMonoMed",
                      width=self.width - 28 * mm - 40 * mm)
            canvas.setStrokeColor(RULE)
            canvas.setLineWidth(0.25)
            canvas.line(0, y - 5 * mm, self.width - 36 * mm, y - 5 * mm)
            y -= 6.5 * mm
        draw_roundel(canvas, self.width - 15 * mm, self.height - 15 * mm, 15 * mm, self.edition, ACCENT)


def list_cells(draft: MagazineDraft, magazine_id: str) -> tuple[list[Flowable], dict[str, list[MagazineSource]]]:
    cells: list[Flowable] = []
    sources: dict[str, list[MagazineSource]] = {}
    counts = Counter((record.group, record.title) for record in draft.records)
    seen: Counter = Counter()
    last_initial = ""
    chapter = plate = 0
    for index, artist in enumerate(draft.artists):
        records = sorted([record for record in draft.records if record.group == artist.name], key=record_order)
        if not records:
            continue
        if initial(artist.name) != last_initial:
            last_initial = initial(artist.name)
            cells.append(LetterMarker(last_initial, f"letter-{last_initial}-{index}"))
        chapter += 1
        cells.append(ArtistCard(artist, [(1, artist.name, f"artist-{index}")], chapter, len(records)))
        collected = list(artist.sources)
        for record in records:
            seen[(record.group, record.title)] += 1
            plate += 1
            title = record.title or "Untitled record"
            if counts[(record.group, record.title)] > 1:
                title += (f" / {record.catalog_number}" if record.catalog_number else "") + \
                         f" / Copy {seen[(record.group, record.title)]}"
            cells.append(AlbumCard(record, title, magazine_id, draft.settings.include_notes,
                                   [(2, title, f"record-{record.id}")], plate))
            collected.extend(record.sources)
        if collected:
            sources[artist.name] = collected
    return cells, sources


def overview(draft: MagazineDraft, heading_style: ParagraphStyle) -> list[Flowable]:
    body = style("overview", size=9.5, leading=14, after=5)
    story: list[Flowable] = [Spacer(1, 6 * mm), SectionHeading("The collection at a glance", heading_style, "overview", 0)]
    artists = len({record.group for record in draft.records})
    story.extend(paragraphs(f"{len(draft.records)} records · {artists} artists and groups", style("big", "MagazineCond", 20, 24, after=6)))
    years = [record.year for record in draft.records if record.year is not None]
    if years:
        story.extend(paragraphs(f"Released between {min(years)} and {max(years)}", body))
    genres = Counter(genre for record in draft.records for genre in record.genres)
    if genres:
        story.extend(paragraphs("Genres: " + ", ".join(f"{genre} ({count})" for genre, count in genres.most_common(12)), body))
    valued = [record for record in draft.records if record.value_eur is not None]
    if valued:
        total = sum(record.value_eur for record in valued if record.value_eur is not None)
        scope = "" if len(valued) == len(draft.records) else f" across {len(valued)} of {len(draft.records)} records"
        story.extend(paragraphs(f"Estimated value: EUR {total:,.0f}{scope}", style("total", "MagazineCond", 15, 19, color=ACCENT, after=6)))
    return story


def source_line(name: str, items: list[MagazineSource], line_style: ParagraphStyle) -> Paragraph:
    """One line per artist: each website once, linked to the first page used from it."""
    sites: dict[str, MagazineSource] = {}
    for source in items:
        host = (urlparse(source.url).hostname or source.url).removeprefix("www.")
        sites.setdefault(host, source)
    links = ", ".join(f'<link href="{escape(source.url, quote=True)}" color="#d93a2b">{escape(host)}</link>'
                      for host, source in sites.items())
    return Paragraph(f'<font name="MagazineBold">{escape(name)}</font> — {links}', line_style)


def render_magazine(draft: MagazineDraft, magazine_id: str, target: Path, edition: int,
                    check: Callable[[], None],
                    progress: Callable[[int, int, float, float], None] | None = None) -> tuple[int, list[str]]:
    register_fonts()
    _IMAGE_CACHE.clear()
    target.parent.mkdir(parents=True, exist_ok=True)
    document = MagazineDocument(str(target), draft, check, edition)
    heading = style("heading", "MagazineCond", 24, 28, after=8)
    heading.keepWithNext = True
    body = style("body", size=10, leading=14, after=6)

    images = [image for record in draft.records for image in record.images if image.asset]
    cover = next((image for image in images if image.id == draft.settings.cover_image_id), None)
    story: list[Flowable] = [
        CoverPage(asset_path(magazine_id, cover.asset) if cover and cover.asset else None, draft, edition),
        NextPageTemplate("columns"), PageBreak(),
        SectionHeading("Foreword", heading, "foreword", 0),
    ]
    story.extend(paragraphs(draft.settings.preface, body))
    subheading = style("subheading", "MagazineCond", 17, 21, after=5)
    subheading.keepWithNext = True
    story.extend(overview(draft, subheading))
    # Foreword and overview fill the left column of the opening page, the contents start in the right one.
    story.extend([FrameBreak(), SectionHeading("Contents", heading, "contents", 0)])
    toc = TableOfContents()
    toc.levelStyles = [style("toc-artist", "MagazineMonoMed", 8, 12)]
    story.extend([toc, NextPageTemplate("cells"), PageBreak()])
    cells, sources = list_cells(draft, magazine_id)
    if progress:
        # The document is typeset in several passes (contents need page numbers). Each pass spans a third of
        # the percentage; the counter shows the page within the current pass.
        estimate = max(1, len(cells) // 4 + 6)
        state = {"last": 0, "pass": 0}

        def on_page(page: int) -> None:
            if page <= state["last"]:
                state["pass"] += 1
            state["last"] = page
            progress(min(page, estimate), estimate, min(60.0, state["pass"] * 30.0), 30.0)

        document.on_page = on_page
    for cell in cells:
        check()
        story.append(cell)
    sources_text = style("sources", size=7.5, leading=10.5, after=2.5)
    notice = ("Editorial research may be assisted by AI. Prices are the estimates stored in the collection, in EUR, "
              "not binding appraisals. This edition is intended for personal use.")
    column = (TEXT_WIDTH - GUTTER) / 2
    artists = len({record.group for record in draft.records})
    colophon = [("Edition", f"№ {edition:03d} · {draft.snapshot_at[:10]}"),
                ("Records", f"{len(draft.records)} · {artists} artists and groups"),
                ("Catalogue", f"PHX-0001 — PHX-{len(draft.records):04d}"),
                ("Values", "EUR, as stored in the collection"),
                ("Typefaces", "IBM Plex Sans Condensed, Serif, Mono"),
                ("Software", "Phonox")]
    story.extend([NextPageTemplate("columns"), PageBreak(),
                  SectionHeading("Sources", heading, "sources", 0), block(notice, body), Spacer(1, 3 * mm)])
    story.extend(source_line(name, items, sources_text) for name, items in sources.items())
    story.extend([Spacer(1, 8 * mm), Colophon(colophon, edition, column)])
    document.multiBuild(story, maxPasses=6)
    warnings = list(dict.fromkeys(warning for cell in cells for warning in cell.warnings))
    reader = PdfReader(target)
    if reader.is_encrypted or not reader.pages:
        raise RuntimeError("PDF output cannot be opened")
    return len(reader.pages), warnings
