"""
Tests for metadata lookup module (Discogs and MusicBrainz APIs).
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.agent.metadata import (
    lookup_discogs_metadata,
    lookup_musicbrainz_metadata,
    lookup_metadata_from_both,
    _extract_discogs_artist,
    _extract_discogs_label,
    _extract_discogs_catalog,
    _extract_musicbrainz_artist,
    _extract_musicbrainz_year,
    _extract_musicbrainz_label,
    _extract_musicbrainz_catalog,
    MetadataError,
)


class TestLookupDiscogsMetadata:
    """Tests for lookup_discogs_metadata function."""

    def test_discogs_valid_lookup(self):
        """Test successful Discogs metadata lookup."""
        with patch("backend.agent.metadata.requests.get") as mock_get:
            # Mock search response
            search_response = MagicMock()
            search_response.json.return_value = {
                "results": [
                    {
                        "id": 12345,
                        "title": "Abbey Road",
                    }
                ]
            }

            # Mock detail response
            detail_response = MagicMock()
            detail_response.json.return_value = {
                "id": 12345,
                "title": "Abbey Road",
                "year": 1969,
                "artists": [{"name": "The Beatles"}],
                "labels": [{"name": "Apple Records", "catno": "PCS 7088"}],
                "genres": ["Rock", "Pop"],
            }

            mock_get.side_effect = [search_response, detail_response]

            result = lookup_discogs_metadata("The Beatles", "Abbey Road")

            assert result is not None
            assert result["artist"] == "The Beatles"
            assert result["title"] == "Abbey Road"
            assert result["year"] == 1969
            assert result["label"] == "Apple Records"
            assert result["catalog_number"] == "PCS 7088"
            assert result["confidence"] == 0.85

    def test_discogs_not_found(self):
        """Test Discogs lookup when release not found."""
        with patch("backend.agent.metadata.requests.get") as mock_get:
            search_response = MagicMock()
            search_response.json.return_value = {"results": []}
            mock_get.return_value = search_response

            result = lookup_discogs_metadata("Unknown Artist", "Unknown Album")

            assert result is None

    def test_discogs_missing_artist(self):
        """Test that missing artist raises ValueError."""
        with pytest.raises(ValueError):
            lookup_discogs_metadata("", "Abbey Road")

    def test_discogs_api_error_fallback(self):
        """Test Discogs API error with fallback."""
        with patch("backend.agent.metadata.requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection error")

            result = lookup_discogs_metadata(
                "The Beatles",
                "Abbey Road",
                fallback_on_error=True,
            )

            assert result is None

    def test_discogs_api_error_no_fallback(self):
        """Test Discogs API error raises MetadataError."""
        with patch("backend.agent.metadata.requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection error")

            with pytest.raises(MetadataError):
                lookup_discogs_metadata(
                    "The Beatles",
                    "Abbey Road",
                    fallback_on_error=False,
                )

    def test_discogs_partial_data(self):
        """Test Discogs lookup with partial data."""
        with patch("backend.agent.metadata.requests.get") as mock_get:
            search_response = MagicMock()
            search_response.json.return_value = {
                "results": [{"id": 12345}]
            }

            detail_response = MagicMock()
            detail_response.json.return_value = {
                "id": 12345,
                "title": "Album Title",
                "year": None,
                "artists": [],
                "labels": [],
                "genres": [],
            }

            mock_get.side_effect = [search_response, detail_response]

            result = lookup_discogs_metadata("Artist", "Album")

            assert result is not None
            assert result["title"] == "Album Title"


class TestLookupMusicBrainzMetadata:
    """Tests for lookup_musicbrainz_metadata function."""

    def test_musicbrainz_valid_lookup(self):
        """Test successful MusicBrainz metadata lookup."""
        with patch("backend.agent.metadata.requests.get") as mock_get:
            response = MagicMock()
            response.json.return_value = {
                "releases": [
                    {
                        "title": "Abbey Road",
                        "date": "1969-09-26",
                        "artist-credit": [
                            {
                                "artist": {"name": "The Beatles"}
                            }
                        ],
                        "label-info": [
                            {
                                "label": {"name": "Apple Records"},
                                "catalog-number": "PCS 7088",
                            }
                        ],
                        "tags": [
                            {"name": "rock"},
                            {"name": "pop"},
                        ],
                    }
                ]
            }
            mock_get.return_value = response

            result = lookup_musicbrainz_metadata("The Beatles", "Abbey Road")

            assert result is not None
            assert result["artist"] == "The Beatles"
            assert result["title"] == "Abbey Road"
            assert result["year"] == 1969
            assert result["label"] == "Apple Records"
            assert result["catalog_number"] == "PCS 7088"
            assert result["confidence"] == 0.80

    def test_musicbrainz_not_found(self):
        """Test MusicBrainz lookup when release not found."""
        with patch("backend.agent.metadata.requests.get") as mock_get:
            response = MagicMock()
            response.json.return_value = {"releases": []}
            mock_get.return_value = response

            result = lookup_musicbrainz_metadata("Unknown Artist", "Unknown Album")

            assert result is None

    def test_musicbrainz_api_error_fallback(self):
        """Test MusicBrainz API error with fallback."""
        with patch("backend.agent.metadata.requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection error")

            result = lookup_musicbrainz_metadata(
                "The Beatles",
                "Abbey Road",
                fallback_on_error=True,
            )

            assert result is None

    def test_musicbrainz_api_error_no_fallback(self):
        """Test MusicBrainz API error raises MetadataError."""
        with patch("backend.agent.metadata.requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection error")

            with pytest.raises(MetadataError):
                lookup_musicbrainz_metadata(
                    "The Beatles",
                    "Abbey Road",
                    fallback_on_error=False,
                )


class TestExtractDiscogsMetadata:
    """Tests for Discogs metadata extraction functions."""

    def test_extract_discogs_artist(self):
        """Test extracting artist from Discogs data."""
        release = {
            "artists": [{"name": "The Beatles"}],
        }
        assert _extract_discogs_artist(release) == "The Beatles"

    def test_extract_discogs_artist_fallback(self):
        """Test extracting artist from title fallback."""
        release = {
            "artists": [],
            "title": "The Beatles - Abbey Road",
        }
        assert _extract_discogs_artist(release) == "The Beatles"

    def test_extract_discogs_label(self):
        """Test extracting label from Discogs data."""
        release = {
            "labels": [{"name": "Apple Records"}],
        }
        assert _extract_discogs_label(release) == "Apple Records"

    def test_extract_discogs_catalog(self):
        """Test extracting catalog number from Discogs data."""
        release = {
            "labels": [{"name": "Apple Records", "catno": "PCS 7088"}],
        }
        assert _extract_discogs_catalog(release) == "PCS 7088"

    def test_extract_discogs_catalog_missing(self):
        """Test extracting missing catalog number."""
        release = {
            "labels": [{"name": "Apple Records"}],
        }
        assert _extract_discogs_catalog(release) is None


class TestExtractMusicBrainzMetadata:
    """Tests for MusicBrainz metadata extraction functions."""

    def test_extract_musicbrainz_artist(self):
        """Test extracting artist from MusicBrainz data."""
        release = {
            "artist-credit": [
                {"artist": {"name": "The Beatles"}}
            ],
        }
        assert _extract_musicbrainz_artist(release) == "The Beatles"

    def test_extract_musicbrainz_artist_missing(self):
        """Test extracting missing artist."""
        release = {"artist-credit": []}
        assert _extract_musicbrainz_artist(release) == "Unknown"

    def test_extract_musicbrainz_year(self):
        """Test extracting year from MusicBrainz data."""
        release = {"date": "1969-09-26"}
        assert _extract_musicbrainz_year(release) == 1969

    def test_extract_musicbrainz_year_invalid_date(self):
        """Test extracting year from invalid date."""
        release = {"date": "invalid"}
        assert _extract_musicbrainz_year(release) is None

    def test_extract_musicbrainz_label(self):
        """Test extracting label from MusicBrainz data."""
        release = {
            "label-info": [
                {"label": {"name": "Apple Records"}}
            ],
        }
        assert _extract_musicbrainz_label(release) == "Apple Records"

    def test_extract_musicbrainz_catalog(self):
        """Test extracting catalog number from MusicBrainz data."""
        release = {
            "label-info": [
                {"catalog-number": "PCS 7088"}
            ],
        }
        assert _extract_musicbrainz_catalog(release) == "PCS 7088"


class TestLookupMetadataFromBoth:
    """Tests for lookup_metadata_from_both function."""

    def test_both_apis_success(self):
        """Test successful lookup from both APIs."""
        with patch("backend.agent.metadata.lookup_discogs_metadata") as mock_discogs, \
             patch("backend.agent.metadata.lookup_musicbrainz_metadata") as mock_mb:
            
            mock_discogs.return_value = {
                "artist": "The Beatles",
                "title": "Abbey Road",
                "year": 1969,
                "label": "Apple Records",
                "catalog_number": "PCS 7088",
                "genres": ["Rock"],
                "confidence": 0.85,
            }
            mock_mb.return_value = {
                "artist": "The Beatles",
                "title": "Abbey Road",
                "year": 1969,
                "label": "Apple Records",
                "catalog_number": "PCS 7088",
                "genres": ["Rock"],
                "confidence": 0.80,
            }

            discogs_result, mb_result = lookup_metadata_from_both("The Beatles", "Abbey Road")

            assert discogs_result is not None
            assert mb_result is not None
            assert discogs_result["confidence"] == 0.85
            assert mb_result["confidence"] == 0.80

    def test_one_api_fails(self):
        """Test when one API fails."""
        with patch("backend.agent.metadata.lookup_discogs_metadata") as mock_discogs, \
             patch("backend.agent.metadata.lookup_musicbrainz_metadata") as mock_mb:
            
            mock_discogs.return_value = None
            mock_mb.return_value = {
                "artist": "The Beatles",
                "title": "Abbey Road",
                "year": 1969,
                "label": "Apple Records",
                "catalog_number": "PCS 7088",
                "genres": ["Rock"],
                "confidence": 0.80,
            }

            discogs_result, mb_result = lookup_metadata_from_both("The Beatles", "Abbey Road")

            assert discogs_result is None
            assert mb_result is not None

    def test_both_apis_fail(self):
        """Test when both APIs fail."""
        with patch("backend.agent.metadata.lookup_discogs_metadata") as mock_discogs, \
             patch("backend.agent.metadata.lookup_musicbrainz_metadata") as mock_mb:
            
            mock_discogs.return_value = None
            mock_mb.return_value = None

            discogs_result, mb_result = lookup_metadata_from_both("Unknown", "Unknown")

            assert discogs_result is None
            assert mb_result is None


class TestMetadataIntegration:
    """Integration tests for metadata lookups."""

    def test_discogs_full_flow(self):
        """Test complete Discogs lookup flow."""
        with patch("backend.agent.metadata.requests.get") as mock_get:
            search_response = MagicMock()
            search_response.json.return_value = {
                "results": [
                    {
                        "id": 999,
                        "title": "Test Album",
                    }
                ]
            }

            detail_response = MagicMock()
            detail_response.json.return_value = {
                "id": 999,
                "title": "Test Album",
                "year": 2020,
                "artists": [{"name": "Test Artist"}],
                "labels": [{"name": "Test Label", "catno": "TEST001"}],
                "genres": ["Electronic"],
            }

            mock_get.side_effect = [search_response, detail_response]

            result = lookup_discogs_metadata("Test Artist", "Test Album")

            assert result is not None
            assert result["artist"] == "Test Artist"
            assert result["label"] == "Test Label"
            assert result["genres"] == ["Electronic"]

    def test_musicbrainz_full_flow(self):
        """Test complete MusicBrainz lookup flow."""
        with patch("backend.agent.metadata.requests.get") as mock_get:
            response = MagicMock()
            response.json.return_value = {
                "releases": [
                    {
                        "title": "Test Album",
                        "date": "2020-01-15",
                        "artist-credit": [
                            {"artist": {"name": "Test Artist"}}
                        ],
                        "label-info": [
                            {
                                "label": {"name": "Test Label"},
                                "catalog-number": "TEST001",
                            }
                        ],
                        "tags": [
                            {"name": "electronic"},
                        ],
                    }
                ]
            }
            mock_get.return_value = response

            result = lookup_musicbrainz_metadata("Test Artist", "Test Album")

            assert result is not None
            assert result["artist"] == "Test Artist"
            assert result["year"] == 2020
            assert result["label"] == "Test Label"

    def test_timeout_handling(self):
        """Test timeout handling in metadata lookups."""
        with patch("backend.agent.metadata.requests.get") as mock_get:
            mock_get.side_effect = TimeoutError("Request timeout")

            result = lookup_discogs_metadata(
                "Test",
                "Album",
                fallback_on_error=True,
            )

            assert result is None
