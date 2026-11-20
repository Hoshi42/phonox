"""Landscape A4 magazine: compact album and artist cards, four albums per page.

Missing information is simply left out; the layout never mentions what is unknown.
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
MARGIN_TOP = 15 * mm
MARGIN_BOTTOM = 14 * mm
GUTTER = 8 * mm
FRAME_HEIGHT = PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM
CELL_WIDTH = (PAGE_WIDTH - 2 * MARGIN_X - GUTTER) / 2
TEXT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X
PAD = 4 * mm
CARD_GAP = 2 * mm
COVER_SIZE = 32 * mm
THUMB_SIZE = (COVER_SIZE - 2 * mm) / 2
TEXT_MAX_HEIGHT = 52 * mm
MAX_IMAGES = 3
PORTRAIT_MAX_HEIGHT = 46 * mm
IMAGE_DPI = 200
COVER_DPI = 150

INK = colors.HexColor("#20282a")
MUTED = colors.HexColor("#6b7274")
ACCENT = colors.HexColor("#a45f37")
PAPER = colors.HexColor("#faf7f1")
CARD = colors.white
RULE = colors.HexColor("#e2dccf")
TINT = colors.HexColor("#f1ebe0")


def register_fonts() -> None:
    root = Path("/usr/share/fonts/truetype/dejavu")
    for name, filename in [
        ("MagazineBody", "DejaVuSans.ttf"),
        ("MagazineBold", "DejaVuSans-Bold.ttf"),
        ("MagazineSerif", "DejaVuSerif.ttf"),
    ]:
        if name not in pdfmetrics.getRegisteredFontNames():
            path = root / filename
            if not path.is_file():
                raise RuntimeError("Magazine fonts missing. Install fonts-dejavu-core or rebuild the backend image.")
            pdfmetrics.registerFont(TTFont(name, str(path)))
    pdfmetrics.registerFontFamily("MagazineBody", normal="MagazineBody", bold="MagazineBold",
                                 italic="MagazineBody", boldItalic="MagazineBold")


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
    def __init__(self, filename: str, draft: MagazineDraft, check: Callable[[], None]):
        super().__init__(filename, pagesize=landscape(A4), leftMargin=MARGIN_X, rightMargin=MARGIN_X,
                         topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM,
                         title=draft.settings.title, author=draft.settings.display_name or "Phonox")
        self.check = check
        self.magazine_title = draft.settings.title
        self.on_page: Callable[[int], None] | None = None

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

    def draw_cover_page(self, canvas, doc):
        self.check()
        canvas.setFillColor(PAPER)
        canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)

    def draw_page(self, canvas, doc):
        self.check()
        if self.on_page:
            self.on_page(doc.page)
        canvas.setFillColor(PAPER)
        canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)
        canvas.setFont("MagazineBody", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN_X, 7 * mm, self.magazine_title[:90])
        canvas.drawRightString(PAGE_WIDTH - MARGIN_X, 7 * mm, str(doc.page))
        canvas.setStrokeColor(RULE)
        canvas.line(MARGIN_X, 10.5 * mm, PAGE_WIDTH - MARGIN_X, 10.5 * mm)

    def afterFlowable(self, flowable):
        for level, title, key in getattr(flowable, "entries", []):
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, level=level, closed=False)
            if getattr(flowable, "contents", False):
                self.notify("TOCEntry", (level, escape(title), self.page, key))


_IMAGE_CACHE: dict[tuple, tuple[bytes, float, float]] = {}


def embedded(path: Path, width: float, height: float, crop: bool, dpi: int = IMAGE_DPI,
             quality: int = 80) -> tuple[ImageReader, float, float]:
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
    canvas.roundRect(x, y, width, height, 2 * mm, stroke=0, fill=1)
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


class Card(Flowable):
    """A white card as wide as one half page; its height depends on the content."""

    def __init__(self, height: float, entries: list[tuple[int, str, str]]):
        super().__init__()
        self.width, self.height = CELL_WIDTH, height
        self.entries = entries
        self.contents = False
        self.spaceAfter = CARD_GAP
        self.warnings: list[str] = []

    def draw_card(self) -> None:
        canvas = self.canv
        canvas.setFillColor(CARD)
        canvas.setStrokeColor(RULE)
        canvas.roundRect(0, 0, self.width, self.height, 2.5 * mm, stroke=1, fill=1)


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
    def __init__(self, record: MagazineRecord, title: str, magazine_id: str, include_notes: bool,
                 entries: list[tuple[int, str, str]]):
        super().__init__(0, entries)
        self.record, self.title, self.magazine_id, self.include_notes = record, title, magazine_id, include_notes
        self.images = [image for image in record.images if image.asset][:MAX_IMAGES]
        self.text_x = PAD + (COVER_SIZE + 4 * mm if self.images else 0)
        self.items = self.layout(self.width - PAD - self.text_x)

    def facts(self) -> str:
        record = self.record
        parts = [str(record.year) if record.year else "", record.label or "",
                 f"Cat. {record.catalog_number}" if record.catalog_number else "", record.condition or ""]
        return " · ".join(part for part in parts if part)

    def value_markup(self) -> str:
        record = self.record
        if record.value_eur is None:
            return ""
        label = "Market estimate" if record.value_kind == "researched" else "Estimate"
        if record.valued_at:
            label += f" · {record.valued_at[:10]}"
        return (f'<font name="MagazineBold" color="#a45f37" size="10">EUR {record.value_eur:,.0f}</font>'
                f' <font color="#6b7274" size="6.5">{escape(label)}</font>')

    def layout(self, text_w: float) -> list[Paragraph]:
        """Text paragraphs; the card is as tall as the photographs or the text, whichever is taller."""
        record = self.record
        items: list[Paragraph] = []
        if record.artist and artist_name(record.artist).casefold() != record.group.casefold():
            items.append(block(record.artist.upper(), style("kicker", "MagazineBold", 7, color=ACCENT, after=1)))
        for size in (13, 12, 11, 10):
            heading = block(self.title, style("album-title", "MagazineSerif", size, size * 1.18, after=1.5 * mm))
            if heading.wrap(text_w, 100)[1] <= size * 1.18 * 2 + 0.1:
                break
        items.append(heading)
        genres = ", ".join(record.genres)
        for index, (markup, color) in enumerate(((escape(self.facts()), INK), (escape(genres), MUTED),
                                                 (self.value_markup(), INK))):
            if markup:
                items.append(Paragraph(markup, style(f"line-{index}", size=7.5, color=color, after=2)))
        for item in items:
            item.wrap(text_w, 100)
        used = sum(item.height + item.style.spaceAfter for item in items)
        photos = (COVER_SIZE + (2 * mm + THUMB_SIZE if len(self.images) > 1 else 0)) if self.images else 0
        limit = max(photos, TEXT_MAX_HEIGHT)
        notes = record.notes if self.include_notes and record.notes else ""
        body = "\n\n".join(part for part in (record.description.strip(), notes.strip()) if part)
        if body:
            paragraphs_, truncated = fit_text(body, text_w, limit - used, sizes=(8.5, 8, 7.5, 7))
            if truncated:
                self.warnings.append(f"Text shortened to fit its card: {self.title}.")
            items.extend(paragraphs_)
            used += sum(item.height + item.style.spaceAfter for item in paragraphs_)
        self.height = 2 * PAD + max(photos, used - items[-1].style.spaceAfter)
        return items

    def draw(self):
        self.draw_card()
        canvas = self.canv
        top = self.height - PAD
        if self.images:
            draw_image(canvas, self.magazine_id, self.images[0], PAD, top - COVER_SIZE, COVER_SIZE, COVER_SIZE)
            for index, image in enumerate(self.images[1:]):
                draw_image(canvas, self.magazine_id, image, PAD + index * (THUMB_SIZE + 2 * mm),
                           top - COVER_SIZE - 2 * mm - THUMB_SIZE, THUMB_SIZE, THUMB_SIZE)
        draw_paragraphs(canvas, self.items, self.text_x, top)


class ArtistCard(Card):
    """Artist name, one-line facts and portrait; its height follows the text."""

    def __init__(self, artist: MagazineArtist, entries: list[tuple[int, str, str]]):
        super().__init__(0, entries)
        self.artist = artist
        self.keepWithNext = True
        inner = self.width - 2 * PAD
        for size in (18, 16, 14, 12):
            heading = block(artist.name, style("artist-name", "MagazineSerif", size, size * 1.15))
            if heading.wrap(inner, 100)[1] <= size * 1.15 * 2 + 0.1:
                break
        self.items: list[Paragraph] = [heading]
        heading.style.spaceAfter = 1.5 * mm
        if artist.facts.strip():
            facts = block(artist.facts.strip(), style("artist-facts", "MagazineBold", 7.5, color=ACCENT, after=1.5 * mm))
            facts.wrap(inner, 40)
            self.items.append(facts)
        used = sum(item.height + item.style.spaceAfter for item in self.items)
        if artist.portrait.strip():
            portrait, truncated = fit_text(artist.portrait, inner, PORTRAIT_MAX_HEIGHT - 2 * PAD - used,
                                           sizes=(8.5, 8, 7.5))
            if truncated:
                self.warnings.append(f"Portrait shortened to fit its card: {artist.name}.")
            self.items.extend(portrait)
        total = sum(item.height + item.style.spaceAfter for item in self.items)
        self.height = 2 * PAD + total - self.items[-1].style.spaceAfter

    def draw(self):
        self.draw_card()
        draw_paragraphs(self.canv, self.items, PAD, self.height - PAD)


class CoverPage(Flowable):
    def __init__(self, path: Path | None, draft: MagazineDraft, edition: int):
        super().__init__()
        self.width, self.height = PAGE_WIDTH, PAGE_HEIGHT - 0.5
        self.path, self.draft, self.edition = path, draft, edition

    def draw(self):
        canvas, settings = self.canv, self.draft.settings
        subtitle = " · ".join(part for part in (
            settings.subtitle, settings.display_name, f"Edition {self.edition}", self.draft.snapshot_at[:10]) if part)
        if self.path:
            with PillowImage.open(self.path) as source:
                photo = ImageOps.fit(source.convert("RGB"), (int(PAGE_WIDTH / 72 * COVER_DPI), int(PAGE_HEIGHT / 72 * COVER_DPI)),
                                     method=PillowImage.Resampling.LANCZOS)
            data = BytesIO()
            photo.save(data, "JPEG", quality=80, optimize=True)
            data.seek(0)
            canvas.drawImage(ImageReader(data), 0, 0, PAGE_WIDTH, PAGE_HEIGHT)
            panel_h = 48 * mm
            canvas.setFillColor(colors.HexColor("#182022"))
            canvas.rect(0, 0, PAGE_WIDTH, panel_h, stroke=0, fill=1)
            color, left, width = colors.white, MARGIN_X, TEXT_WIDTH
            top_text = panel_h - 8 * mm
        else:
            color, left, width = INK, 30 * mm, PAGE_WIDTH - 60 * mm
            top_text = PAGE_HEIGHT - 55 * mm
            canvas.setFillColor(ACCENT)
            canvas.setFont("MagazineBold", 9)
            canvas.drawString(left, top_text + 14 * mm, "PHONOX · THE COLLECTION EDITION")
        for size in (34, 26, 20, 14):
            heading = Paragraph(escape(settings.title), ParagraphStyle(
                "cover-title", fontName="MagazineSerif", fontSize=size, leading=size * 1.2, textColor=color))
            _, h = heading.wrap(width, 100 * mm)
            if h <= (30 * mm if self.path else 60 * mm):
                break
        heading.drawOn(canvas, left, top_text - h)
        if subtitle:
            sub = Paragraph(escape(subtitle), ParagraphStyle(
                "cover-sub", fontName="MagazineBody", fontSize=9, leading=12, textColor=color))
            _, sub_h = sub.wrap(width, 20 * mm)
            sub.drawOn(canvas, left, top_text - h - 3 * mm - sub_h)


def list_cells(draft: MagazineDraft, magazine_id: str) -> tuple[list[Flowable], dict[str, list[MagazineSource]]]:
    cells: list[Flowable] = []
    sources: dict[str, list[MagazineSource]] = {}
    counts = Counter((record.group, record.title) for record in draft.records)
    seen: Counter = Counter()
    last_initial = ""
    for index, artist in enumerate(draft.artists):
        records = sorted([record for record in draft.records if record.group == artist.name], key=record_order)
        if not records:
            continue
        if initial(artist.name) != last_initial:
            last_initial = initial(artist.name)
            cells.append(LetterMarker(last_initial, f"letter-{last_initial}-{index}"))
        cells.append(ArtistCard(artist, [(1, artist.name, f"artist-{index}")]))
        collected = list(artist.sources)
        for record in records:
            seen[(record.group, record.title)] += 1
            title = record.title or "Untitled record"
            if counts[(record.group, record.title)] > 1:
                title += (f" / {record.catalog_number}" if record.catalog_number else "") + \
                         f" / Copy {seen[(record.group, record.title)]}"
            cells.append(AlbumCard(record, title, magazine_id, draft.settings.include_notes,
                                   [(2, title, f"record-{record.id}")]))
            collected.extend(record.sources)
        if collected:
            sources[artist.name] = collected
    return cells, sources


def overview(draft: MagazineDraft, heading_style: ParagraphStyle) -> list[Flowable]:
    body = style("overview", size=9.5, leading=14, after=5)
    story: list[Flowable] = [Spacer(1, 6 * mm), SectionHeading("The collection at a glance", heading_style, "overview", 0)]
    artists = len({record.group for record in draft.records})
    story.extend(paragraphs(f"{len(draft.records)} records · {artists} artists and groups", style("big", "MagazineSerif", 14, after=6)))
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
        story.extend(paragraphs(f"Estimated value: EUR {total:,.0f}{scope}", style("total", "MagazineBold", 12, color=ACCENT, after=6)))
    return story


def source_line(name: str, items: list[MagazineSource], line_style: ParagraphStyle) -> Paragraph:
    """One line per artist: each website once, linked to the first page used from it."""
    sites: dict[str, MagazineSource] = {}
    for source in items:
        host = (urlparse(source.url).hostname or source.url).removeprefix("www.")
        sites.setdefault(host, source)
    links = ", ".join(f'<link href="{escape(source.url, quote=True)}" color="#a45f37">{escape(host)}</link>'
                      for host, source in sites.items())
    return Paragraph(f'<font name="MagazineBold">{escape(name)}</font> — {links}', line_style)


def render_magazine(draft: MagazineDraft, magazine_id: str, target: Path, edition: int,
                    check: Callable[[], None],
                    progress: Callable[[int, int, float, float], None] | None = None) -> tuple[int, list[str]]:
    register_fonts()
    _IMAGE_CACHE.clear()
    target.parent.mkdir(parents=True, exist_ok=True)
    document = MagazineDocument(str(target), draft, check)
    heading = style("heading", "MagazineSerif", 20, 24, after=8)
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
    subheading = style("subheading", "MagazineSerif", 15, 18, after=5)
    subheading.keepWithNext = True
    story.extend(overview(draft, subheading))
    # Foreword and overview fill the left column of the opening page, the contents start in the right one.
    story.extend([FrameBreak(), SectionHeading("Contents", heading, "contents", 0)])
    toc = TableOfContents()
    toc.levelStyles = [style("toc-artist", "MagazineBody", 8, 11)]
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
    notice = ("Editorial research may be assisted by AI. Prices are market estimates in EUR, not binding "
              "appraisals. This edition is intended for personal use.")
    story.extend([NextPageTemplate("columns"), PageBreak(),
                  SectionHeading("Sources", heading, "sources", 0), block(notice, body), Spacer(1, 3 * mm)])
    story.extend(source_line(name, items, sources_text) for name, items in sources.items())
    document.multiBuild(story, maxPasses=6)
    warnings = list(dict.fromkeys(warning for cell in cells for warning in cell.warnings))
    reader = PdfReader(target)
    if reader.is_encrypted or not reader.pages:
        raise RuntimeError("PDF output cannot be opened")
    return len(reader.pages), warnings
