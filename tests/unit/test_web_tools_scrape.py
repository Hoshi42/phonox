"""Scraping skips Discogs pages, which always answer HTTP 403."""

from unittest.mock import patch

from backend.tools.web_tools import WebScrapingTool


def test_discogs_pages_are_not_scraped():
    tool = WebScrapingTool()
    with patch.object(WebScrapingTool, "scrape_url", side_effect=lambda url, max_chars: {"url": url}) as scrape:
        results = tool.scrape_multiple_urls(
            ["https://www.discogs.com/release/1-x", "https://example.org/price", "https://www.discogs.com/artist/2-y"]
        )

    assert [item["url"] for item in results] == ["https://example.org/price"]
    scrape.assert_called_once()
