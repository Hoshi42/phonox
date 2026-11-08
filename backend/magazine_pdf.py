"""Editorial A4 magazine typesetting with embedded images, fonts and linked contents."""

from collections import Counter
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Callable

from PIL import Image as PillowImage, ImageOps
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, Image, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer,
)
from reportlab.platypus.tableofcontents import TableOfContents

from backend.magazine_models import MagazineDraft, MagazineImage, MagazineRecord, MagazineSource
from backend.magazine_service import asset_path, record_order

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 18 * mm
WIDTH = PAGE_WIDTH - 2 * MARGIN
HEIGHT = PAGE_HEIGHT - 2 * MARGIN
INK = colors.HexColor("#20282a")
ACCENT = colors.HexColor("#a45f37")
PAPER = colors.HexColor("#faf7f1")


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


def styles() -> dict[str, ParagraphStyle]:
    return {
        "body": ParagraphStyle("body", fontName="MagazineBody", fontSize=11, leading=17,
                               textColor=INK, spaceAfter=12),
        "heading": ParagraphStyle("heading", fontName="MagazineSerif", fontSize=32, leading=39,
                                  textColor=INK, spaceAfter=18, keepWithNext=True),
        "article": ParagraphStyle("article", fontName="MagazineSerif", fontSize=25, leading=31,
                                  textColor=INK, spaceAfter=14, keepWithNext=True),
        "kicker": ParagraphStyle("kicker", fontName="MagazineBold", fontSize=10, leading=14,
                                 textColor=ACCENT, spaceAfter=10, keepWithNext=True),
        "caption": ParagraphStyle("caption", fontName="MagazineBody", fontSize=8.5, leading=12,
                                  textColor=INK, spaceAfter=10),
        "value": ParagraphStyle("value", fontName="MagazineBold", fontSize=13, leading=18,
                                textColor=ACCENT, spaceBefore=12, spaceAfter=8),
    }


def paragraphs(text: str, style: ParagraphStyle) -> list[Flowable]:
    return [Paragraph(escape(part).replace("\n", "<br/>"), style)
            for part in text.split("\n\n") if part.strip()]


class SectionHeading(Paragraph):
    def __init__(self, text: str, style: ParagraphStyle, key: str, level: int):
        super().__init__(escape(text), style)
        self.section_title, self.section_key, self.section_level = text, key, level


class MagazineDocument(BaseDocTemplate):
    def __init__(self, filename: str, draft: MagazineDraft, check: Callable[[], None]):
        super().__init__(filename, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=MARGIN, bottomMargin=MARGIN,
                         title=draft.settings.title, author=draft.settings.display_name or "Phonox")
        self.check = check
        self.chapter = ""
        self.addPageTemplates(PageTemplate(
            id="editorial", frames=Frame(MARGIN, MARGIN, WIDTH, HEIGHT,
                                        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
            onPage=self.draw_page,
        ))

    def beforeDocument(self):
        self.chapter = ""

    def draw_page(self, canvas, doc):
        self.check()
        canvas.setFillColor(PAPER)
        canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)
        if doc.page > 1:
            canvas.setFont("MagazineBody", 8)
            canvas.setFillColor(INK)
            canvas.drawString(MARGIN, 10 * mm, self.chapter[:65])
            canvas.drawRightString(PAGE_WIDTH - MARGIN, 10 * mm, str(doc.page))
            canvas.setStrokeColor(ACCENT)
            canvas.line(MARGIN, PAGE_HEIGHT - 10 * mm, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 10 * mm)

    def afterFlowable(self, flowable):
        if isinstance(flowable, SectionHeading):
            self.canv.bookmarkPage(flowable.section_key)
            self.canv.addOutlineEntry(flowable.section_title, flowable.section_key,
                                      level=flowable.section_level, closed=False)
            self.notify("TOCEntry", (flowable.section_level, escape(flowable.section_title),
                                     self.page, flowable.section_key))
            if flowable.section_level == 0:
                self.chapter = flowable.section_title


class PhotoPage(Flowable):
    """Decorative full-bleed photograph; the uncut original also appears in its article."""
    def __init__(self, path: Path, title: str, subtitle: str, number: bool = True):
        super().__init__()
        self.width, self.height = WIDTH, HEIGHT
        self.path, self.title, self.subtitle, self.number = path, title, subtitle, number

    def draw(self):
        with PillowImage.open(self.path) as source:
            dpi = min(300, source.width / (PAGE_WIDTH / 72), source.height / (PAGE_HEIGHT / 72))
            size = (max(1, int(PAGE_WIDTH / 72 * dpi)), max(1, int(PAGE_HEIGHT / 72 * dpi)))
            photo = ImageOps.fit(source, size, method=PillowImage.Resampling.LANCZOS)
            data = BytesIO()
            photo.save(data, "JPEG", quality=92)
        canvas = self.canv
        canvas.drawImage(ImageReader(data), -MARGIN, -MARGIN,
                         width=PAGE_WIDTH, height=PAGE_HEIGHT, mask="auto")
        panel_height = 55 * mm
        canvas.setFillColor(colors.HexColor("#182022"))
        canvas.rect(-MARGIN, -MARGIN, PAGE_WIDTH, panel_height, stroke=0, fill=1)
        for font_size in (30, 22, 16, 12):
            heading = Paragraph(escape(self.title), ParagraphStyle(
                "photo-title", fontName="MagazineSerif", fontSize=font_size, leading=font_size * 1.2,
                textColor=colors.white))
            _, height = heading.wrap(WIDTH, 31 * mm)
            if height <= 31 * mm:
                break
        if height > 31 * mm:
            raise ValueError("Title too long for the photograph page; use a shorter magazine title")
        heading.drawOn(canvas, 0, 34 * mm - height)
        sub = Paragraph(escape(self.subtitle), ParagraphStyle(
            "photo-subtitle", fontName="MagazineBody", fontSize=8, leading=11, textColor=colors.white))
        _, sub_height = sub.wrap(WIDTH, 20 * mm)
        if sub_height > 20 * mm:
            raise ValueError("Subtitle too long for the photograph page")
        sub.drawOn(canvas, 0, 2 * mm - sub_height)
        if self.number:
            canvas.setFont("MagazineBody", 8)
            canvas.setFillColor(colors.white)
            canvas.setFillColor(INK)
            canvas.rect(WIDTH - 8 * mm, HEIGHT - 5 * mm, 10 * mm, 8 * mm, fill=1, stroke=0)
            canvas.setFillColor(colors.white)
            canvas.drawRightString(WIDTH, HEIGHT - 2 * mm, str(canvas.getPageNumber()))


class PortraitColumns(Flowable):
    def __init__(self, text: str, style: ParagraphStyle):
        super().__init__()
        words = text.split()
        middle = len(words) // 2
        self.left = Paragraph(escape(" ".join(words[:middle])), style)
        self.right = Paragraph(escape(" ".join(words[middle:])), style)
        self.column_width = (WIDTH - 8 * mm) / 2
        self.width = WIDTH
        self.height = max(self.left.wrap(self.column_width, HEIGHT)[1],
                          self.right.wrap(self.column_width, HEIGHT)[1])

    def draw(self):
        self.left.drawOn(self.canv, 0, self.height - self.left.height)
        self.right.drawOn(self.canv, self.column_width + 8 * mm, self.height - self.right.height)


def suitable_photo(image: MagazineImage) -> bool:
    # 150 dpi at A4 size after the decorative portrait crop.
    return bool(image.asset and min(image.width / (PAGE_WIDTH / 72),
                                    image.height / (PAGE_HEIGHT / 72)) >= 150)


def photo_flowable(image: MagazineImage, magazine_id: str, caption: str,
                   sheet_styles: dict[str, ParagraphStyle], warnings: list[str]) -> list[Flowable]:
    if not image.asset:
        return paragraphs(f"Image unavailable: {image.filename}", sheet_styles["caption"])
    path = asset_path(magazine_id, image.asset)
    scale = min(WIDTH / image.width, 200 * mm / image.height)
    width, height = image.width * scale, image.height * scale
    dpi = min(image.width / (width / 72), image.height / (height / 72))
    if dpi < 150:
        warnings.append(f"Low print resolution ({dpi:.0f} dpi): {image.filename} ({image.id}).")
    return [KeepTogether([Image(str(path), width=width, height=height),
                          Spacer(1, 4 * mm), Paragraph(escape(caption), sheet_styles["caption"])])]


def source_paragraphs(sources: list[MagazineSource], sheet_styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    return [Paragraph(
        f'<link href="{escape(source.url, quote=True)}" color="#a45f37">'
        f'{escape(source.title)}</link> — accessed {escape(source.accessed_at[:10])}',
        sheet_styles["caption"],
    ) for source in sources]


def record_metadata(record: MagazineRecord) -> str:
    parts = [
        f"Year: {record.year if record.year is not None else 'unknown'}",
        f"Label: {record.label or 'not recorded'}",
        f"Catalogue: {record.catalog_number or 'not recorded'}",
        f"Condition: {record.condition or 'not recorded'}",
    ]
    if record.genres:
        parts.append("Genres: " + ", ".join(record.genres))
    return " · ".join(parts)


def render_magazine(draft: MagazineDraft, magazine_id: str, target: Path, edition: int,
                    check: Callable[[], None]) -> tuple[int, list[str]]:
    register_fonts()
    sheet_styles = styles()
    target.parent.mkdir(parents=True, exist_ok=True)
    document = MagazineDocument(str(target), draft, check)
    story: list[Flowable] = []
    warnings: list[str] = []
    images = [image for record in draft.records for image in record.images if image.asset]
    cover = next((image for image in images if image.id == draft.settings.cover_image_id), None)
    if draft.settings.cover_image_id and cover is None:
        warnings.append("Selected cover image is no longer available; typographic cover used.")
    if cover:
        assert cover.asset is not None
        story.append(PhotoPage(asset_path(magazine_id, cover.asset), draft.settings.title,
                               f"{draft.settings.subtitle} · {draft.settings.display_name} · Edition {edition} · {draft.snapshot_at[:10]}",
                               number=False))
        if not suitable_photo(cover):
            warnings.append("Selected cover has insufficient resolution for a 150 dpi full-page print.")
    else:
        story.extend([Spacer(1, 35 * mm),
                      Paragraph("PHONOX / THE COLLECTION EDITION", sheet_styles["kicker"])])
        story.extend(paragraphs(draft.settings.title, sheet_styles["heading"]))
        story.extend(paragraphs(draft.settings.subtitle, sheet_styles["body"]))
        story.extend(paragraphs(draft.settings.display_name, sheet_styles["body"]))
        story.append(Paragraph(f"Edition {edition} · {draft.snapshot_at[:10]}", sheet_styles["caption"]))
        story.extend([Spacer(1, 28 * mm),
                      Paragraph("Records. Artists. Stories.", sheet_styles["article"])])
    story.append(PageBreak())
    story.append(SectionHeading("Foreword", sheet_styles["heading"], "foreword", 0))
    story.extend(paragraphs(draft.settings.preface, sheet_styles["body"]))
    story.append(PageBreak())
    story.append(SectionHeading("Contents", sheet_styles["heading"], "contents", 0))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("toc-artist", fontName="MagazineBold", fontSize=11, leading=17, spaceBefore=9),
        ParagraphStyle("toc-record", fontName="MagazineBody", fontSize=10, leading=15, leftIndent=14),
    ]
    story.extend([toc, PageBreak()])
    story.append(SectionHeading("The collection at a glance", sheet_styles["heading"], "overview", 0))
    story.extend(paragraphs(f"{len(draft.records)} records · {len(draft.artists)} artist chapters",
                            sheet_styles["article"]))
    years = [record.year for record in draft.records if record.year is not None]
    if years:
        story.extend(paragraphs(f"Recorded release years: {min(years)}–{max(years)}", sheet_styles["body"]))
    genres = Counter(genre for record in draft.records for genre in record.genres)
    if genres:
        story.extend(paragraphs("Genres: " + ", ".join(f"{genre} ({count})" for genre, count in genres.most_common()),
                                sheet_styles["body"]))
    for kind, label in [("researched", "Research-based estimates"), ("stored", "Stored estimates (dates unknown)")]:
        valued = [record for record in draft.records if record.value_kind == kind and record.value_eur is not None]
        if valued:
            total = sum(record.value_eur for record in valued if record.value_eur is not None)
            story.extend(paragraphs(f"{label}: EUR {total:,.2f} "
                                    f"across {len(valued)} copies.", sheet_styles["value"]))
    count = sum(record.value_eur is not None for record in draft.records)
    story.extend(paragraphs(
        f"Valuation coverage: {count} of {len(draft.records)} copies. "
        "Missing values are not zero. Research-based estimates may have different dates; "
        "see each article. All values are non-binding estimates, not appraisals or guaranteed sale prices.",
        sheet_styles["body"]))
    story.extend(paragraphs(f"Collection snapshot: {draft.snapshot_at[:19]} UTC. "
                            f"Research steps used: {draft.steps_used} of 20.", sheet_styles["caption"]))
    titles = Counter((record.group, record.title) for record in draft.records)
    exemplar_counts: Counter = Counter()
    all_sources: list[tuple[str, list[MagazineSource]]] = []
    for index, artist in enumerate(draft.artists):
        check()
        records = sorted([record for record in draft.records if record.group == artist.name], key=record_order)
        story.append(PageBreak())
        story.append(Paragraph(f"ARTIST PORTRAIT / {index + 1:02d}", sheet_styles["kicker"]))
        story.append(SectionHeading(artist.name, sheet_styles["heading"], f"artist-{index}", 0))
        if 70 <= len(artist.portrait.split()) <= 350:
            columns = PortraitColumns(artist.portrait, sheet_styles["body"])
            if columns.height <= HEIGHT - 70 * mm:
                story.extend([columns, Spacer(1, 5 * mm)])
            else:
                story.extend(paragraphs(artist.portrait, sheet_styles["body"]))
        else:
            story.extend(paragraphs(artist.portrait, sheet_styles["body"]))
        if artist.sources:
            all_sources.append((artist.name, artist.sources))
            story.extend(paragraphs("Research sources are listed in the closing source notes.", sheet_styles["caption"]))
        image = next((image for record in records for image in record.images if suitable_photo(image)), None)
        if image:
            assert image.asset is not None
            story.extend([PageBreak(), PhotoPage(asset_path(magazine_id, image.asset), artist.name,
                                                "From the collection / album artwork, not an artist photograph")])
        else:
            warnings.append(f"No image suitable for a large-format 150 dpi chapter photograph: {artist.name}.")
        for record in records:
            story.append(PageBreak())
            exemplar_counts[(record.group, record.title)] += 1
            article_title = record.title or "Untitled record"
            if titles[(record.group, record.title)] > 1:
                article_title += (f" / {record.catalog_number}" if record.catalog_number else "") + \
                                 f" / Copy {exemplar_counts[(record.group, record.title)]}"
            story.append(Paragraph(escape(record.artist or "Unknown Artist"), sheet_styles["kicker"]))
            story.append(SectionHeading(article_title, sheet_styles["article"], f"record-{record.id}", 1))
            story.extend(paragraphs(record_metadata(record), sheet_styles["caption"]))
            if record.images:
                story.extend(photo_flowable(record.images[0], magazine_id, "The documented copy / main image",
                                            sheet_styles, warnings))
            else:
                story.extend(paragraphs("No photographs are available for this copy.", sheet_styles["caption"]))
            story.extend(paragraphs(record.description, sheet_styles["body"]))
            label = "Research-based estimate" if record.value_kind == "researched" else "Stored estimate"
            value_text = f"{label}: EUR {record.value_eur:,.2f}" if record.value_eur is not None else "Value unavailable"
            story.extend(paragraphs(value_text, sheet_styles["value"]))
            date_text = record.valued_at[:10] if record.valued_at else "unknown"
            story.extend(paragraphs(f"Valuation date: {date_text}. {record.valuation_note}", sheet_styles["caption"]))
            if draft.settings.include_notes and record.notes:
                story.extend(paragraphs("Collector's notes", sheet_styles["kicker"]))
                story.extend(paragraphs(record.notes, sheet_styles["body"]))
            for image_index, image in enumerate(record.images[1:], start=2):
                story.extend([PageBreak(), Paragraph("FROM THE COLLECTION / IMAGE GALLERY", sheet_styles["kicker"])])
                story.extend(paragraphs(article_title, sheet_styles["article"]))
                story.extend(photo_flowable(image, magazine_id, f"View {image_index} / {image.filename}",
                                            sheet_styles, warnings))
            if record.sources:
                all_sources.append((f"{artist.name} / {article_title}", record.sources))
    story.extend([PageBreak(), SectionHeading("Sources & edition notes", sheet_styles["heading"], "sources", 0)])
    story.extend(paragraphs(
        "Editorial research may be assisted by AI and was offered for review before publication. "
        "Collection details and photographs come from the saved snapshot. Database search candidates "
        "do not prove a particular pressing. Prices are market estimates in EUR, not binding appraisals. "
        "This edition is intended for personal use; public distribution may require additional image permissions.",
        sheet_styles["body"]))
    for name, sources in all_sources:
        story.extend(paragraphs(name, sheet_styles["kicker"]))
        story.extend(source_paragraphs(sources, sheet_styles))
    combined_warnings = list(dict.fromkeys(draft.warnings + warnings))
    if combined_warnings:
        story.extend(paragraphs("Data & image quality notes", sheet_styles["article"]))
        for warning in combined_warnings:
            story.extend(paragraphs(warning, sheet_styles["caption"]))
    document.multiBuild(story, maxPasses=6)
    if not target.is_file() or target.stat().st_size < 1000:
        raise RuntimeError("PDF output is missing or incomplete")
    reader = PdfReader(target)
    if reader.is_encrypted or not reader.pages:
        raise RuntimeError("PDF output cannot be opened")
    return len(reader.pages), warnings
