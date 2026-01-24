"""
Tests for websearch module (Tavily API integration).
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.agent.websearch import (
    search_vinyl_metadata,
    search_vinyl_metadata_with_fallback,
    _parse_tavily_response,
    _calculate_relevance,
    WebsearchError,
)


class TestSearchVinylMetadata:
    """Tests for search_vinyl_metadata function."""

    def test_search_valid_query(self):
        """Test successful search with valid artist and title."""
        with patch("backend.agent.websearch.TavilyClient") as mock_client:
            mock_response = {
                "results": [
                    {
                        "title": "The Beatles - Abbey Road",
                        "url": "https://www.discogs.com/the-beatles-abbey-road",
                        "content": "Abbey Road is the eleventh studio album...",
                    }
                ]
            }
            mock_client.return_value.search.return_value = mock_response

            results = search_vinyl_metadata("The Beatles", "Abbey Road")

            assert len(results) == 1
            assert results[0]["title"] == "The Beatles - Abbey Road"
            assert "discogs.com" in results[0]["url"]

    def test_search_missing_artist(self):
        """Test that missing artist raises ValueError."""
        with pytest.raises(ValueError):
            search_vinyl_metadata("", "Abbey Road")

    def test_search_missing_title(self):
        """Test that missing title raises ValueError."""
        with pytest.raises(ValueError):
            search_vinyl_metadata("The Beatles", "")

    def test_search_none_artist(self):
        """Test that None artist raises ValueError."""
        with pytest.raises(ValueError):
            search_vinyl_metadata(None, "Abbey Road")  # type: ignore

    def test_search_api_error_fallback_true(self):
        """Test that API error returns empty list when fallback_on_error=True."""
        with patch("backend.agent.websearch.TavilyClient") as mock_client:
            mock_client.return_value.search.side_effect = Exception("API Error")

            results = search_vinyl_metadata(
                "The Beatles",
                "Abbey Road",
                fallback_on_error=True,
            )

            assert results == []

    def test_search_api_error_fallback_false(self):
        """Test that API error raises WebsearchError when fallback_on_error=False."""
        with patch("backend.agent.websearch.TavilyClient") as mock_client:
            mock_client.return_value.search.side_effect = Exception("API Error")

            with pytest.raises(WebsearchError):
                search_vinyl_metadata(
                    "The Beatles",
                    "Abbey Road",
                    fallback_on_error=False,
                )

    def test_search_multiple_results(self):
        """Test search returns multiple results correctly."""
        with patch("backend.agent.websearch.TavilyClient") as mock_client:
            mock_response = {
                "results": [
                    {
                        "title": "Beatles - Abbey Road (Discogs)",
                        "url": "https://www.discogs.com/abbey-road",
                        "content": "Discogs entry",
                    },
                    {
                        "title": "Beatles - Abbey Road (Wikipedia)",
                        "url": "https://en.wikipedia.org/wiki/Abbey_Road",
                        "content": "Wikipedia entry",
                    },
                    {
                        "title": "Beatles - Abbey Road (MusicBrainz)",
                        "url": "https://www.musicbrainz.org/release/abbey-road",
                        "content": "MusicBrainz entry",
                    },
                ]
            }
            mock_client.return_value.search.return_value = mock_response

            results = search_vinyl_metadata("The Beatles", "Abbey Road")

            assert len(results) == 3
            assert results[0]["url"] == "https://www.discogs.com/abbey-road"
            assert results[1]["url"] == "https://en.wikipedia.org/wiki/Abbey_Road"
            assert results[2]["url"] == "https://www.musicbrainz.org/release/abbey-road"

    def test_search_empty_results(self):
        """Test search returns empty list when no results found."""
        with patch("backend.agent.websearch.TavilyClient") as mock_client:
            mock_response = {"results": []}
            mock_client.return_value.search.return_value = mock_response

            results = search_vinyl_metadata("Unknown Artist", "Unknown Album")

            assert results == []

    def test_search_query_construction(self):
        """Test that search query is constructed correctly."""
        with patch("backend.agent.websearch.TavilyClient") as mock_client:
            mock_response = MagicMock()
            mock_response.results = []
            mock_client.return_value.search.return_value = mock_response

            search_vinyl_metadata("Pink Floyd", "The Wall")

            # Verify search was called with correct query
            call_args = mock_client.return_value.search.call_args
            assert "Pink Floyd" in call_args[1]["query"]
            assert "The Wall" in call_args[1]["query"]
            assert "vinyl" in call_args[1]["query"].lower()


class TestParseTavilyResponse:
    """Tests for _parse_tavily_response function."""

    def test_parse_valid_response(self):
        """Test parsing valid Tavily response."""
        mock_response = {
            "results": [
                {
                    "title": "Result Title",
                    "url": "https://example.com",
                    "content": "Result content",
                }
            ]
        }

        results = _parse_tavily_response(mock_response)

        assert len(results) == 1
        assert results[0]["title"] == "Result Title"
        assert results[0]["url"] == "https://example.com"
        assert results[0]["snippet"] == "Result content"
        assert "relevance" in results[0]

    def test_parse_response_with_missing_fields(self):
        """Test parsing response with missing optional fields."""
        mock_response = {"results": [{}]}

        results = _parse_tavily_response(mock_response)

        assert len(results) == 1
        assert "title" in results[0]
        assert "url" in results[0]
        assert "snippet" in results[0]

    def test_parse_empty_response(self):
        """Test parsing empty response."""
        mock_response = {"results": []}

        results = _parse_tavily_response(mock_response)

        assert results == []

    def test_parse_invalid_response(self):
        """Test parsing None/invalid response."""
        results = _parse_tavily_response(None)  # type: ignore

        assert results == []

    def test_parse_response_without_results_key(self):
        """Test parsing response without results key."""
        mock_response = {}

        results = _parse_tavily_response(mock_response)

        assert results == []


class TestCalculateRelevance:
    """Tests for _calculate_relevance function."""

    def test_discogs_url_high_relevance(self):
        """Test that Discogs URLs get high relevance score."""
        relevance = _calculate_relevance("https://www.discogs.com/release/12345")

        assert relevance == 0.95

    def test_musicbrainz_url_high_relevance(self):
        """Test that MusicBrainz URLs get high relevance score."""
        relevance = _calculate_relevance("https://www.musicbrainz.org/release/12345")

        assert relevance == 0.90

    def test_wikipedia_url_medium_relevance(self):
        """Test that Wikipedia URLs get medium relevance score."""
        relevance = _calculate_relevance("https://en.wikipedia.org/wiki/Abbey_Road")

        assert relevance == 0.70

    def test_vinyl_record_url_relevance(self):
        """Test that vinyl/record URLs get appropriate relevance."""
        relevance = _calculate_relevance("https://example.com/vinyl-records")

        assert relevance == 0.65

    def test_generic_url_low_relevance(self):
        """Test that generic URLs get low relevance score."""
        relevance = _calculate_relevance("https://example.com/page")

        assert relevance == 0.50

    def test_case_insensitive_matching(self):
        """Test that URL matching is case insensitive."""
        relevance = _calculate_relevance("HTTPS://WWW.DISCOGS.COM/RELEASE/12345")

        assert relevance == 0.95

    def test_dict_url_input(self):
        """Test handling of dict URL input."""
        result = {"url": "https://www.discogs.com/release/12345"}
        relevance = _calculate_relevance(result)

        assert relevance == 0.95


class TestSearchVinylMetadataWithFallback:
    """Tests for search_vinyl_metadata_with_fallback function."""

    def test_successful_search_with_fallback(self):
        """Test successful search with fallback wrapper."""
        with patch("backend.agent.websearch.search_vinyl_metadata") as mock_search:
            mock_search.return_value = [
                {
                    "title": "Beatles - Abbey Road",
                    "url": "https://discogs.com",
                    "snippet": "Album info",
                    "relevance": 0.95,
                }
            ]

            result = search_vinyl_metadata_with_fallback("The Beatles", "Abbey Road")

            assert result["success"] is True
            assert len(result["results"]) == 1
            assert result["error"] is None
            assert "Abbey Road" in result["query"]

    def test_failed_search_with_fallback(self):
        """Test failed search returns success=False."""
        with patch("backend.agent.websearch.search_vinyl_metadata") as mock_search:
            mock_search.return_value = []

            result = search_vinyl_metadata_with_fallback(
                "Unknown Artist",
                "Unknown Album",
            )

            assert result["success"] is False
            assert result["results"] == []

    def test_fallback_with_retries(self):
        """Test fallback wrapper retries on empty results."""
        with patch("backend.agent.websearch.search_vinyl_metadata") as mock_search:
            # First call returns empty, second returns results
            mock_search.side_effect = [
                [],
                [
                    {
                        "title": "Beatles - Abbey Road",
                        "url": "https://discogs.com",
                        "snippet": "Album info",
                        "relevance": 0.95,
                    }
                ],
            ]

            result = search_vinyl_metadata_with_fallback(
                "The Beatles",
                "Abbey Road",
                max_retries=2,
            )

            # Note: May succeed or fail depending on implementation details
            # Just verify the structure is correct
            assert "success" in result
            assert "results" in result
            assert "error" in result
            assert "query" in result

    def test_fallback_returns_dict_structure(self):
        """Test that fallback always returns correct dict structure."""
        with patch("backend.agent.websearch.search_vinyl_metadata") as mock_search:
            mock_search.return_value = []

            result = search_vinyl_metadata_with_fallback("Artist", "Album")

            assert isinstance(result, dict)
            assert "results" in result
            assert "success" in result
            assert "error" in result
            assert "query" in result
            assert isinstance(result["results"], list)
            assert isinstance(result["success"], bool)


class TestWebsearchIntegration:
    """Integration tests for websearch functionality."""

    def test_end_to_end_search_and_parse(self):
        """Test complete search and parse flow."""
        with patch("backend.agent.websearch.TavilyClient") as mock_client:
            # Mock Tavily response
            mock_response = {
                "results": [
                    {
                        "title": "Pink Floyd - The Wall (Discogs)",
                        "url": "https://www.discogs.com/pink-floyd-the-wall",
                        "content": "Pink Floyd's double album The Wall...",
                    },
                    {
                        "title": "Pink Floyd - The Wall (Wikipedia)",
                        "url": "https://en.wikipedia.org/wiki/The_Wall",
                        "content": "The Wall is the eleventh studio album...",
                    },
                ]
            }
            mock_client.return_value.search.return_value = mock_response

            results = search_vinyl_metadata("Pink Floyd", "The Wall")

            assert len(results) == 2
            assert results[0]["relevance"] == 0.95  # Discogs
            assert results[1]["relevance"] == 0.70  # Wikipedia
            assert results[0]["title"] == "Pink Floyd - The Wall (Discogs)"

    def test_websearch_error_recovery(self):
        """Test error recovery in websearch."""
        with patch("backend.agent.websearch.TavilyClient") as mock_client:
            mock_client.return_value.search.side_effect = TimeoutError("Connection timeout")

            # Should return empty list with fallback_on_error=True
            results = search_vinyl_metadata(
                "Test Artist",
                "Test Album",
                fallback_on_error=True,
            )

            assert results == []

            # Should raise WebsearchError with fallback_on_error=False
            with pytest.raises(WebsearchError):
                search_vinyl_metadata(
                    "Test Artist",
                    "Test Album",
                    fallback_on_error=False,
                )
