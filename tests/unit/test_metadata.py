"""
Tests for metadata lookup module (Discogs and MusicBrainz APIs).
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.agent.metadata import (
    lookup_discogs_metadata,
    lookup_musicbrainz_metadata,
    lookup_metadata_from_both,
    format_discogs_market_context,
    musicbrainz_enabled,
    _score_discogs_candidate,
    _extract_discogs_artist,
    _extract_discogs_label,
    _extract_discogs_catalog,
    _extract_musicbrainz_artist,
    _extract_musicbrainz_year,
    _extract_musicbrainz_label,
    _extract_musicbrainz_catalog,
    MetadataError,
)


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    """MusicBrainz is off by default (the tests exercise it); never use a real Discogs token."""
    monkeypatch.setenv("MUSICBRAINZ_ENABLED", "true")
    monkeypatch.delenv("DISCOGS_TOKEN", raising=False)


def _response(payload, status=200):
    mock = MagicMock()
    mock.json.return_value = payload
    mock.status_code = status
    return mock


DANZIG_HITS = {
    "results": [
        {"id": 1, "title": "Danzig - Danzig", "year": "2024", "catno": "DEF 24208",
         "format": ["Vinyl", "LP", "Reissue", "Unofficial Release"], "label": ["Def American Recordings"],
         "community": {"have": 300}},
        {"id": 2, "title": "Danzig - Danzig", "year": "1988", "catno": "DEF 24208",
         "format": ["Vinyl", "LP", "Album"], "label": ["Def American Recordings"],
         "community": {"have": 1467}},
        {"id": 3, "title": "Danzig - Danzig", "year": "1988", "catno": "9 24208-2",
         "format": ["CD", "Album"], "label": ["Def American Recordings"], "community": {"have": 900}},
    ]
}

DANZIG_RELEASE = {
    "id": 2,
    "title": "Danzig",
    "year": 1988,
    "country": "US",
    "uri": "https://www.discogs.com/release/2-Danzig-Danzig",
    "artists": [{"name": "Danzig"}],
    "labels": [{"name": "Def American Recordings", "catno": "DEF 24208"}],
    "genres": ["Rock"],
    "formats": [{"name": "Vinyl", "descriptions": ["LP", "Album"]}],
    "lowest_price": 167.0,
    "num_for_sale": 20,
    "community": {"have": 1467, "want": 1785, "rating": {"average": 4.73}},
}


class TestDiscogsExactPressing:
    """Exact pressing selection and marketplace data."""

    def test_catalog_number_selects_original_pressing(self):
        with patch("backend.agent.metadata.requests.get") as mock_get:
            mock_get.side_effect = [_response(DANZIG_HITS), _response(DANZIG_RELEASE)]

            result = lookup_discogs_metadata(
                "Danzig", "Danzig", catalog_number="DEF 24208", year=1988, label="Def American"
            )

        assert result["discogs_release_id"] == 2
        assert result["exact_match"] is True
        assert result["match_basis"] == "catalog_number"
        assert result["confidence"] == 0.92
        assert result["country"] == "US"
        assert result["format"] == "Vinyl, LP, Album"
        first_search = mock_get.call_args_list[0]
        assert first_search.kwargs["params"]["catno"] == "DEF 24208"

    def test_marketplace_figures_are_returned_in_eur(self):
        with patch("backend.agent.metadata.requests.get") as mock_get:
            mock_get.side_effect = [_response(DANZIG_HITS), _response(DANZIG_RELEASE)]

            result = lookup_discogs_metadata("Danzig", "Danzig", catalog_number="DEF 24208", year=1988)

        assert mock_get.call_args_list[1].kwargs["params"] == {"curr_abbr": "EUR"}
        assert result["marketplace"]["currency"] == "EUR"
        assert result["marketplace"]["lowest_price"] == 167.0
        assert result["marketplace"]["num_for_sale"] == 20
        assert result["marketplace"]["have"] == 1467

    def test_falls_back_to_artist_title_when_catalog_number_finds_nothing(self):
        with patch("backend.agent.metadata.requests.get") as mock_get:
            mock_get.side_effect = [
                _response({"results": []}),
                _response({"results": [{"id": 7, "title": "Danzig - Danzig", "year": "1988",
                                        "format": ["Vinyl", "LP"]}]}),
                _response({**DANZIG_RELEASE, "id": 7, "labels": [{"name": "Other", "catno": "X-1"}]}),
            ]

            result = lookup_discogs_metadata("Danzig", "Danzig", catalog_number="DEF 24208")

        assert result["discogs_release_id"] == 7
        assert result["exact_match"] is False
        assert result["match_basis"] == "artist_title"
        assert result["confidence"] == 0.85
        assert mock_get.call_args_list[1].kwargs["params"]["release_title"] == "Danzig"

    def test_catalog_number_alone_is_enough_without_title(self):
        with patch("backend.agent.metadata.requests.get") as mock_get:
            mock_get.side_effect = [_response(DANZIG_HITS), _response(DANZIG_RELEASE)]

            result = lookup_discogs_metadata("Danzig", "", catalog_number="DEF 24208", year=1988)

        assert result["title"] == "Danzig"
        assert result["exact_match"] is True
        assert mock_get.call_count == 2  # no artist/title search without a title

    def test_title_or_identifier_is_required(self):
        with pytest.raises(ValueError):
            lookup_discogs_metadata("Danzig", "")

    def test_search_errors_are_not_reported_as_no_match(self):
        with patch("backend.agent.metadata.requests.get", side_effect=ConnectionError("down")):
            with pytest.raises(MetadataError):
                lookup_discogs_metadata("Danzig", "Danzig", catalog_number="DEF 24208", fallback_on_error=False)

    def test_barcode_match_counts_as_exact(self):
        hit = {"id": 5, "title": "A - B", "barcode": ["0 7599-24208 1"], "format": ["Vinyl"]}
        score, basis = _score_discogs_candidate(hit, "A", "B", None, "07599242082", None, None)
        assert basis is None
        score, basis = _score_discogs_candidate(hit, "A", "B", None, "0 7599-24208 1", None, None)
        assert basis == "barcode"

    def test_unofficial_and_non_vinyl_hits_rank_lower(self):
        official = {"id": 1, "title": "A - B", "year": "1988", "format": ["Vinyl", "LP"]}
        bootleg = {"id": 2, "title": "A - B", "year": "1988", "format": ["Vinyl", "LP", "Unofficial Release"]}
        cd = {"id": 3, "title": "A - B", "year": "1988", "format": ["CD"]}
        scores = [_score_discogs_candidate(h, "A", "B", None, None, 1988, None)[0] for h in (official, bootleg, cd)]
        assert scores[0] > scores[1] > scores[2]

    def test_price_suggestions_only_with_token(self, monkeypatch):
        suggestions = _response({"Near Mint (NM or M-)": {"currency": "EUR", "value": 150.5}})
        monkeypatch.delenv("DISCOGS_TOKEN", raising=False)
        with patch("backend.agent.metadata.requests.get") as mock_get:
            mock_get.side_effect = [_response(DANZIG_HITS), _response(DANZIG_RELEASE)]
            assert lookup_discogs_metadata("Danzig", "Danzig", catalog_number="DEF 24208")[
                "marketplace"]["price_suggestions"] is None
            assert mock_get.call_count == 2

        monkeypatch.setenv("DISCOGS_TOKEN", "secret")
        with patch("backend.agent.metadata.requests.get") as mock_get:
            mock_get.side_effect = [_response(DANZIG_HITS), _response(DANZIG_RELEASE), suggestions]
            result = lookup_discogs_metadata("Danzig", "Danzig", catalog_number="DEF 24208")
        assert result["marketplace"]["price_suggestions"] == {"Near Mint (NM or M-)": 150.5}

    def test_price_suggestions_without_seller_settings_are_ignored(self, monkeypatch):
        monkeypatch.setenv("DISCOGS_TOKEN", "secret")
        with patch("backend.agent.metadata.requests.get") as mock_get:
            mock_get.side_effect = [_response(DANZIG_HITS), _response(DANZIG_RELEASE), _response({}, status=404)]
            result = lookup_discogs_metadata("Danzig", "Danzig", catalog_number="DEF 24208")
        assert result["marketplace"]["price_suggestions"] is None
        assert result["marketplace"]["lowest_price"] == 167.0

    def test_market_context_describes_pressing_and_prices(self):
        discogs = {
            "discogs_release_id": 2, "artist": "Danzig", "title": "Danzig", "year": 1988,
            "label": "Def American Recordings", "catalog_number": "DEF 24208", "country": "US",
            "format": "Vinyl, LP, Album", "exact_match": True,
            "discogs_url": "https://www.discogs.com/release/2",
            "marketplace": {"lowest_price": 167.0, "num_for_sale": 20, "have": 1467, "want": 1785,
                            "price_suggestions": {"Near Mint (NM or M-)": 150.5}},
        }
        text = format_discogs_market_context(discogs)
        assert "EXACT pressing" in text
        assert "€167.00" in text and "20 copies for sale" in text
        assert "Near Mint (NM or M-): €150.50" in text
        discogs["exact_match"] = False
        assert "NOT confirmed" in format_discogs_market_context(discogs)
        assert format_discogs_market_context(None) == ""


class TestMusicBrainzSwitch:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("MUSICBRAINZ_ENABLED", raising=False)
        assert musicbrainz_enabled() is False
        with patch("backend.agent.metadata.requests.get") as mock_get:
            assert lookup_musicbrainz_metadata("The Beatles", "Abbey Road") is None
            mock_get.assert_not_called()

    def test_can_be_enabled(self, monkeypatch):
        monkeypatch.setenv("MUSICBRAINZ_ENABLED", "true")
        assert musicbrainz_enabled() is True

    def test_from_both_passes_pressing_hints_to_discogs(self):
        with patch("backend.agent.metadata.lookup_discogs_metadata") as mock_discogs, \
             patch("backend.agent.metadata.lookup_musicbrainz_metadata") as mock_mb:
            mock_discogs.return_value = {"artist": "Danzig"}
            mock_mb.return_value = None
            lookup_metadata_from_both("Danzig", "Danzig", catalog_number="DEF 24208", year=1988)
        assert mock_discogs.call_args.kwargs["catalog_number"] == "DEF 24208"
        assert mock_discogs.call_args.kwargs["year"] == 1988


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
