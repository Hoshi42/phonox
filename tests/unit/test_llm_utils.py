"""Tests for reading Messages API responses."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.agent.llm_utils import content_text, response_text


def _message(*blocks, stop_reason="end_turn"):
    return SimpleNamespace(content=list(blocks), stop_reason=stop_reason)


def test_reads_text_after_a_thinking_block():
    thinking = SimpleNamespace(type="thinking", thinking="", signature="x")  # no .text attribute
    answer = SimpleNamespace(type="text", text='{"ok": true}')
    assert response_text(_message(thinking, answer)) == '{"ok": true}'


def test_joins_multiple_text_blocks():
    message = _message(SimpleNamespace(type="text", text="a"), SimpleNamespace(type="text", text="b"))
    assert response_text(message) == "ab"


def test_empty_content_gives_empty_text():
    assert response_text(_message()) == ""
    assert response_text(SimpleNamespace(content=None, stop_reason=None)) == ""


def test_truncated_response_is_logged(caplog):
    with caplog.at_level("WARNING"):
        response_text(_message(SimpleNamespace(type="text", text="{"), stop_reason="max_tokens"))
    assert "max_tokens" in caplog.text


def test_content_text_drops_thinking_blocks_of_chat_messages():
    blocks = [
        {"type": "thinking", "thinking": "", "signature": "abc"},
        {"type": "text", "text": "Hello "},
        {"type": "text", "text": "world"},
    ]
    assert content_text(blocks) == "Hello world"


def test_content_text_passes_strings_and_handles_odd_values():
    assert content_text("plain") == "plain"
    assert content_text(["a", {"type": "text", "text": "b"}]) == "ab"
    assert content_text(None) == ""
    assert content_text([{"type": "thinking", "thinking": "x"}]) == ""


def test_vision_extraction_reads_json_behind_a_thinking_block():
    from backend.agent.vision import extract_vinyl_metadata

    payload = (
        '{"artist": "Danzig", "title": "Danzig", "label": "Def American", "year": 1988, '
        '"genres": ["Rock"], "confidence": 0.9, "catalog_number": "DEF 24208"}'
    )
    message = _message(
        SimpleNamespace(type="thinking", thinking="", signature="x"),
        SimpleNamespace(type="text", text=payload),
    )
    client = MagicMock()
    client.messages.create.return_value = message

    with patch("backend.agent.vision.Anthropic", return_value=client):
        result = extract_vinyl_metadata("aGVsbG8=", "jpeg", fallback_on_error=False)

    assert result["artist"] == "Danzig"
    assert result["catalog_number"] == "DEF 24208"
