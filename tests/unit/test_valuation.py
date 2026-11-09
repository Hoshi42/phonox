"""Tests for the readable market analysis."""

from backend.agent.valuation import format_market_notes, parse_valuation_sections

DISCOGS = {
    "discogs_release_id": 376907,
    "exact_match": True,
    "match_basis": "catalog_number",
    "country": "US",
    "year": 1988,
    "label": "Def American Recordings",
    "catalog_number": "DEF 24208",
    "marketplace": {"lowest_price": 147.65, "num_for_sale": 14, "have": 2690, "want": 2616},
}

INLINE = (
    "ESTIMATED_VALUE: €155.00\n\nPRICE_RANGE: €125.00 - €240.00\n\nMARKET_CONDITION: stable\n\n"
    "FACTORS: Pressing match (exact catalog number); playing condition is unknown; "
    "the lowest asking price of €147.65\n\n"
    "EXPLANATION: The Discogs data is the primary signal.\nIt sets a realistic floor."
)

BULLETS = (
    "**ESTIMATED_VALUE:** €1,250.50\n"
    "**PRICE_RANGE:** €900 - €1,600\n"
    "MARKET_CONDITION: strong\n"
    "FACTORS:\n- Pressing variant (high impact): original first press\n- Condition unknown\n"
    "EXPLANATION: Rare and in demand."
)


def test_sections_are_split_and_continuation_lines_kept():
    sections = parse_valuation_sections(INLINE)
    assert sections["ESTIMATED_VALUE"] == "€155.00"
    assert sections["EXPLANATION"] == "The Discogs data is the primary signal.\nIt sets a realistic floor."


def test_inline_factors_become_bullets_and_raw_tags_disappear():
    notes = format_market_notes(INLINE, DISCOGS)

    assert notes.startswith("Market analysis\nEstimated value: €155 (range €125–€240), stable market")
    assert "Pressing: Discogs release 376907, exact match by catalog number (US, 1988, Def American Recordings, DEF 24208)" in notes
    assert "On Discogs: lowest listing €147.65, 14 copies for sale, 2,690 have / 2,616 want" in notes
    assert "What affects the price:\n- Pressing match (exact catalog number)\n- playing condition is unknown" in notes
    assert "Summary: The Discogs data is the primary signal. It sets a realistic floor." in notes
    assert "ESTIMATED_VALUE" not in notes and "PRICE_RANGE" not in notes


def test_bullet_factors_markdown_and_thousands_separators():
    notes = format_market_notes(BULLETS)

    assert "Estimated value: €1,250.50 (range €900–€1,600), strong market" in notes
    assert "- Pressing variant (high impact): original first press\n- Condition unknown" in notes
    assert "Pressing:" not in notes  # no Discogs data given
    assert "**" not in notes


def test_unconfirmed_pressing_is_marked():
    notes = format_market_notes(INLINE, {**DISCOGS, "exact_match": False})
    assert "Pressing: closest Discogs release 376907 (not confirmed)" in notes


def test_missing_estimate_returns_none():
    assert format_market_notes("I could not find enough data.") is None
    assert format_market_notes("") is None
