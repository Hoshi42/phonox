"""ddgs searches are retried because single calls intermittently return nothing."""

from unittest.mock import MagicMock, patch

from backend.tools import web_tools
from backend.tools.web_tools import WebSearchTool, ddgs_text_with_retry


def _ddgs(*outcomes):
    instance = MagicMock()
    instance.text.side_effect = list(outcomes)
    return instance


def test_retries_after_empty_result_and_error():
    hit = {"title": "T", "href": "https://example.org", "body": "B"}
    instance = _ddgs(Exception("No results found."), [], [hit])

    with patch.object(web_tools, "DDGS", return_value=instance), patch.object(web_tools.time, "sleep"):
        assert ddgs_text_with_retry("query", 5) == [hit]

    assert instance.text.call_count == 3
    assert [call.kwargs["backend"] for call in instance.text.call_args_list] == web_tools.DDGS_BACKENDS


def test_gives_up_with_empty_list_after_max_attempts():
    instance = _ddgs(*[[] for _ in range(web_tools.DDGS_MAX_ATTEMPTS)])

    with patch.object(web_tools, "DDGS", return_value=instance), patch.object(web_tools.time, "sleep"):
        assert ddgs_text_with_retry("query", 5) == []

    assert instance.text.call_count == web_tools.DDGS_MAX_ATTEMPTS


def test_search_tool_maps_results_from_retried_search():
    hit = {"title": "T", "href": "https://example.org", "body": "B"}
    with patch.object(web_tools, "ddgs_text_with_retry", return_value=[hit]):
        assert WebSearchTool()._duckduckgo_search("query") == [
            {"title": "T", "url": "https://example.org", "content": "B", "score": 0.0}
        ]
