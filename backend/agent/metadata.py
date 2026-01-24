"""
Metadata lookup module for Discogs and MusicBrainz APIs.

This module provides vinyl record metadata lookups from two major music databases:
- Discogs: Extensive discography with vinyl-specific data
- MusicBrainz: Community-driven music metadata

Cost: Free (both APIs are free to use)
Note: Requires internet connectivity; handles timeouts gracefully
"""

import logging
import requests
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import quote

logger = logging.getLogger(__name__)

# API endpoints
DISCOGS_API_BASE = "https://api.discogs.com"
MUSICBRAINZ_API_BASE = "https://musicbrainz.org/ws/2"

# Headers for MusicBrainz API (required)
MUSICBRAINZ_HEADERS = {
    "User-Agent": "Phonox/1.0 (https://github.com/hoshhie/phonox)",
    "Accept": "application/json",
}

# Timeout for API calls
API_TIMEOUT = 5  # seconds


class MetadataError(Exception):
    """Raised when metadata lookup fails."""

    pass


def lookup_discogs_metadata(
    artist: str,
    title: str,
    fallback_on_error: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Lookup vinyl record metadata from Discogs API.

    Args:
        artist: Artist or group name
        title: Album/release title
        fallback_on_error: If True, return None on error; if False, raise exception

    Returns:
        Dict with keys: artist, title, year, label, catalog_number, genres, confidence
        Returns None if not found or error occurred

    Raises:
        MetadataError: If lookup fails and fallback_on_error=False
    """
    if not artist or not title:
        raise ValueError("Artist and title are required")

    try:
        logger.info(f"Discogs lookup: {artist} - {title}")

        # Search for the release
        search_query = f"{artist} {title}"
        search_url = f"{DISCOGS_API_BASE}/database/search"
        params: Dict[str, str] = {
            "q": search_query,
            "type": "release",
            "per_page": "1",
        }

        response = requests.get(
            search_url,
            params=params,
            timeout=API_TIMEOUT,
            headers={"User-Agent": "Phonox/1.0"},
        )
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        if not results:
            logger.warning(f"Discogs: No results for {artist} - {title}")
            return None

        # Get the first result
        release = results[0]
        release_id = release.get("id")

        if not release_id:
            logger.warning("Discogs: No release ID found")
            return None

        # Fetch detailed release information
        release_url = f"{DISCOGS_API_BASE}/releases/{release_id}"
        detail_response = requests.get(
            release_url,
            timeout=API_TIMEOUT,
            headers={"User-Agent": "Phonox/1.0"},
        )
        detail_response.raise_for_status()

        release_data = detail_response.json()

        # Extract metadata
        metadata = {
            "artist": _extract_discogs_artist(release_data),
            "title": release_data.get("title", title),
            "year": release_data.get("year"),
            "label": _extract_discogs_label(release_data),
            "catalog_number": _extract_discogs_catalog(release_data),
            "genres": release_data.get("genres", []),
            "confidence": 0.85,  # Discogs is reliable
        }

        logger.info(f"Discogs: Found {metadata['artist']} - {metadata['title']}")
        return metadata

    except Exception as e:
        logger.error(f"Discogs lookup failed: {e}")
        if fallback_on_error:
            return None
        else:
            raise MetadataError(f"Discogs lookup failed: {e}") from e


def lookup_musicbrainz_metadata(
    artist: str,
    title: str,
    fallback_on_error: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Lookup vinyl record metadata from MusicBrainz API.

    Args:
        artist: Artist or group name
        title: Album/release title
        fallback_on_error: If True, return None on error; if False, raise exception

    Returns:
        Dict with keys: artist, title, year, label, catalog_number, genres, confidence
        Returns None if not found or error occurred

    Raises:
        MetadataError: If lookup fails and fallback_on_error=False
    """
    if not artist or not title:
        raise ValueError("Artist and title are required")

    try:
        logger.info(f"MusicBrainz lookup: {artist} - {title}")

        # Search for the release
        search_query = f"{title} AND artist:{artist}"
        search_url = f"{MUSICBRAINZ_API_BASE}/release"
        params: Dict[str, str] = {
            "query": search_query,
            "limit": "1",
            "fmt": "json",
        }

        response = requests.get(
            search_url,
            params=params,
            timeout=API_TIMEOUT,
            headers=MUSICBRAINZ_HEADERS,
        )
        response.raise_for_status()

        data = response.json()
        releases = data.get("releases", [])

        if not releases:
            logger.warning(f"MusicBrainz: No results for {artist} - {title}")
            return None

        release = releases[0]

        # Extract metadata
        metadata = {
            "artist": _extract_musicbrainz_artist(release),
            "title": release.get("title", title),
            "year": _extract_musicbrainz_year(release),
            "label": _extract_musicbrainz_label(release),
            "catalog_number": _extract_musicbrainz_catalog(release),
            "genres": _extract_musicbrainz_genres(release),
            "confidence": 0.80,  # MusicBrainz is reliable but less vinyl-specific
        }

        logger.info(f"MusicBrainz: Found {metadata['artist']} - {metadata['title']}")
        return metadata

    except Exception as e:
        logger.error(f"MusicBrainz lookup failed: {e}")
        if fallback_on_error:
            return None
        else:
            raise MetadataError(f"MusicBrainz lookup failed: {e}") from e


def lookup_metadata_from_both(
    artist: str,
    title: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Lookup metadata from both Discogs and MusicBrainz.

    Args:
        artist: Artist or group name
        title: Album/release title

    Returns:
        Tuple of (discogs_result, musicbrainz_result)
        Either can be None if lookup fails
    """
    discogs_result = lookup_discogs_metadata(artist, title, fallback_on_error=True)
    musicbrainz_result = lookup_musicbrainz_metadata(artist, title, fallback_on_error=True)

    return discogs_result, musicbrainz_result


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _extract_discogs_artist(release: Dict[str, Any]) -> str:
    """Extract artist name from Discogs release data."""
    artists = release.get("artists", [])
    if artists:
        return artists[0].get("name", "Unknown")
    return release.get("title", "Unknown").split(" - ")[0] if " - " in release.get("title", "") else "Unknown"


def _extract_discogs_label(release: Dict[str, Any]) -> str:
    """Extract label name from Discogs release data."""
    labels = release.get("labels", [])
    if labels:
        return labels[0].get("name", "Unknown")
    return "Unknown"


def _extract_discogs_catalog(release: Dict[str, Any]) -> Optional[str]:
    """Extract catalog number from Discogs release data."""
    labels = release.get("labels", [])
    if labels:
        return labels[0].get("catno")
    return None


def _extract_musicbrainz_artist(release: Dict[str, Any]) -> str:
    """Extract artist name from MusicBrainz release data."""
    artist_credit = release.get("artist-credit", [])
    if artist_credit:
        # artist-credit is a list of dicts with 'artist' key
        if isinstance(artist_credit, list) and len(artist_credit) > 0:
            first_artist = artist_credit[0]
            if isinstance(first_artist, dict):
                artist = first_artist.get("artist", {})
                if isinstance(artist, dict):
                    return artist.get("name", "Unknown")
    return "Unknown"


def _extract_musicbrainz_year(release: Dict[str, Any]) -> Optional[int]:
    """Extract release year from MusicBrainz release data."""
    # Try date first, then year
    date = release.get("date")
    if date:
        try:
            return int(date.split("-")[0])
        except (ValueError, IndexError):
            pass
    return None


def _extract_musicbrainz_label(release: Dict[str, Any]) -> str:
    """Extract label name from MusicBrainz release data."""
    label_info = release.get("label-info", [])
    if label_info and len(label_info) > 0:
        label = label_info[0].get("label", {})
        if isinstance(label, dict):
            return label.get("name", "Unknown")
    return "Unknown"


def _extract_musicbrainz_catalog(release: Dict[str, Any]) -> Optional[str]:
    """Extract catalog number from MusicBrainz release data."""
    label_info = release.get("label-info", [])
    if label_info and len(label_info) > 0:
        return label_info[0].get("catalog-number")
    return None


def _extract_musicbrainz_genres(release: Dict[str, Any]) -> List[str]:
    """Extract genres from MusicBrainz release data."""
    # MusicBrainz doesn't directly provide genres in releases
    # but we can try to extract from tags if available
    tags = release.get("tags", [])
    if tags:
        return [tag.get("name", "") for tag in tags if tag.get("name")]
    return []
