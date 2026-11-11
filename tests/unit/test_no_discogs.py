"""Pricing must keep working when Discogs is unavailable (no token, rate limit, outage)."""

from unittest.mock import patch

import backend.main  # noqa: F401  (routes and main import each other; main must load first)
from backend.agent import chat_agent
from backend.agent.valuation import format_market_notes
from backend.api.routes import _discogs_valuation_context

VALUATION = "ESTIMATED_VALUE: €30.00\nPRICE_RANGE: €20.00 - €45.00\nMARKET_CONDITION: stable"


def test_valuation_prompt_has_no_discogs_block_without_evidence():
    assert _discogs_valuation_context({}) == ""
    assert _discogs_valuation_context({"evidence_chain": []}) == ""


def test_market_notes_work_without_discogs_data():
    notes = format_market_notes(VALUATION, None)
    assert notes and "Estimated value: €30" in notes and "€20–€45" in notes


def test_chat_tool_points_to_web_search_when_no_release_found():
    with patch.object(chat_agent, "lookup_discogs_metadata", return_value=None):
        answer = chat_agent.discogs_market_value.invoke({"artist": "Die Sterne", "title": "Für Anfänger"})
    assert "search_vinyl_prices" in answer


def test_chat_tool_points_to_web_search_when_discogs_fails():
    with patch.object(chat_agent, "lookup_discogs_metadata", side_effect=RuntimeError("429")):
        answer = chat_agent.discogs_market_value.invoke({"artist": "Die Sterne", "title": "Für Anfänger"})
    assert "unavailable" in answer and "search_vinyl_prices" in answer
