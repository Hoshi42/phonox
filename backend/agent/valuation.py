"""Turn the valuation answer and Discogs data into a readable market analysis for the user."""

import re
from typing import Any, Dict, List, Optional

MARKERS = ("ESTIMATED_VALUE", "PRICE_RANGE", "MARKET_CONDITION", "FACTORS", "EXPLANATION")
_MARKER_LINE = re.compile(r"^[\s*#_>-]*(%s)[\s*_]*:\s*(.*)$" % "|".join(MARKERS))
_NUMBER = re.compile(r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)")
MAX_FACTORS = 8


def parse_valuation_sections(text: str) -> Dict[str, str]:
    """Split the valuation answer into its marked sections (continuation lines are kept)."""
    sections: Dict[str, List[str]] = {}
    current: Optional[str] = None
    for line in (text or "").splitlines():
        match = _MARKER_LINE.match(line)
        if match:
            current = match.group(1)
            sections[current] = [match.group(2)]
        elif current is not None:
            sections[current].append(line)
    return {key: "\n".join(lines).strip() for key, lines in sections.items()}


def _numbers(text: str) -> List[float]:
    return [float(value.replace(",", "")) for value in _NUMBER.findall(text or "")]


def _euro(value: float) -> str:
    return f"€{value:,.0f}" if float(value).is_integer() else f"€{value:,.2f}"


def _clean(text: str) -> str:
    return re.sub(r"\*\*|__", "", text).strip()


def _factors(text: str) -> List[str]:
    """Factors arrive either as bullet lines or as one line separated by semicolons."""
    lines = [re.sub(r"^\s*(?:[-•*]|\d+[.)])\s*", "", line).strip() for line in text.splitlines()]
    lines = [_clean(line) for line in lines if line]
    if len(lines) == 1 and ";" in lines[0]:
        lines = [part.strip() for part in lines[0].strip("[]").split(";")]
    return [line for line in lines if line][:MAX_FACTORS]


def _pressing_line(discogs: Dict[str, Any]) -> str:
    details = ", ".join(
        str(part) for part in (
            discogs.get("country"), discogs.get("year"), discogs.get("label"), discogs.get("catalog_number")
        ) if part
    )
    if discogs.get("exact_match"):
        basis = "barcode" if discogs.get("match_basis") == "barcode" else "catalog number"
        line = f"Pressing: Discogs release {discogs['discogs_release_id']}, exact match by {basis}"
    else:
        line = f"Pressing: closest Discogs release {discogs['discogs_release_id']} (not confirmed)"
    return f"{line} ({details})" if details else line


def _discogs_line(market: Dict[str, Any]) -> Optional[str]:
    parts = []
    if market.get("lowest_price") is not None:
        parts.append(f"lowest listing {_euro(market['lowest_price'])}")
    if market.get("num_for_sale") is not None:
        parts.append(f"{market['num_for_sale']} copies for sale")
    if market.get("have") is not None and market.get("want") is not None:
        parts.append(f"{market['have']:,} have / {market['want']:,} want")
    return "On Discogs: " + ", ".join(parts) if parts else None


def format_market_notes(valuation_text: str, discogs: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Readable market analysis (estimate, range, pressing, Discogs figures, price factors, summary).

    Returns None when the valuation answer holds no estimate, so callers can fall back.
    """
    sections = parse_valuation_sections(valuation_text)
    estimate = _numbers(sections.get("ESTIMATED_VALUE", ""))
    if not estimate:
        return None

    headline = f"Estimated value: {_euro(estimate[0])}"
    price_range = _numbers(sections.get("PRICE_RANGE", ""))
    if len(price_range) >= 2:
        headline += f" (range {_euro(price_range[0])}–{_euro(price_range[1])})"
    condition = sections.get("MARKET_CONDITION", "").strip().lower()
    if condition in ("strong", "stable", "weak"):
        headline += f", {condition} market"

    blocks = [["Market analysis", headline]]
    if discogs and discogs.get("discogs_release_id"):
        facts = [_pressing_line(discogs)]
        market_line = _discogs_line(discogs.get("marketplace") or {})
        if market_line:
            facts.append(market_line)
        blocks[0].extend(facts)

    factors = _factors(sections.get("FACTORS", ""))
    if factors:
        blocks.append(["What affects the price:"] + [f"- {factor}" for factor in factors])

    explanation = _clean(re.sub(r"\s*\n\s*", " ", sections.get("EXPLANATION", "")))
    if explanation:
        blocks.append([f"Summary: {explanation}"])

    return "\n\n".join("\n".join(block) for block in blocks)
