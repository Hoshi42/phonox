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
            headers={
                "User-Agent": "Phonox/1.0 (vinyl identification app; contact: https://github.com/hoshhie/phonox)"
            },
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
            headers={
                "User-Agent": "Phonox/1.0 (vinyl identification app; contact: https://github.com/hoshhie/phonox)"
            },
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
    
    Note: Discogs API now requires authentication, so we skip it for now.

    Args:
        artist: Artist or group name
        title: Album/release title

    Returns:
        Tuple of (discogs_result, musicbrainz_result)
        discogs_result will be None due to authentication requirement
    """
    # Skip Discogs due to authentication requirement
    logger.info(f"Skipping Discogs lookup (requires auth) for {artist} - {title}")
    discogs_result = None
    
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




def estimate_vinyl_value(
    artist: str,
    title: str,
    year: Optional[int] = None,
    label: Optional[str] = None,
    genres: Optional[List[str]] = None,
    catalog_number: Optional[str] = None,
    condition_score: Optional[float] = None,
) -> Dict[str, float]:
    """
    Estimate vinyl record market value based on metadata.

    Uses heuristics based on:
    - Release year (older = more valuable)
    - Label prestige (Blue Note, Stax, etc. command premium)
    - Genre (Jazz, Prog Rock tend to be more valuable)
    - Catalog number (more specific editions suggest rarity)
    - Condition score (0.0-1.0, higher = better condition)

    Args:
        artist: Artist name
        title: Album title
        year: Release year
        label: Record label
        genres: List of genres
        catalog_number: Catalog number (alphanumeric code)
        condition_score: Condition score (0.0-1.0), optional

    Returns:
        Dict with estimated_value_eur and estimated_value_usd
    """
    # Base value for a standard vinyl record
    base_value_eur = 10.0

    # Year-based multiplier (older records typically more valuable)
    year_multiplier = 1.0
    if year:
        if year < 1960:
            year_multiplier = 4.0  # Very rare (pre-60s)
        elif year < 1970:
            year_multiplier = 2.5  # Rare (60s)
        elif year < 1980:
            year_multiplier = 1.8  # Less common (70s)
        elif year < 1990:
            year_multiplier = 1.2  # Still somewhat valuable (80s)
        else:
            year_multiplier = 1.0  # Modern pressings

    # Label prestige multiplier
    label_multiplier = 1.0
    if label:
        label_lower = label.lower()
        # Premium jazz labels
        if any(premium in label_lower for premium in ['blue note', 'verve', 'prestige', 'riverside']):
            label_multiplier = 3.5
        # Prog rock / collectible labels
        elif any(prog in label_lower for prog in ['atlantic', 'warner', 'virgin', 'rainbow']):
            label_multiplier = 2.0
        # Classical / specialized
        elif any(classical in label_lower for classical in ['decca', 'philips', 'emi', 'deutsche grammophon']):
            label_multiplier = 1.8
        # Major labels (standard)
        elif any(major in label_lower for major in ['emi', 'sony', 'universal', 'bmi']):
            label_multiplier = 1.1

    # Genre multiplier (some genres command higher prices)
    genre_multiplier = 1.0
    if genres:
        genres_lower = [g.lower() for g in genres]
        # High-value genres
        if any(genre in ' '.join(genres_lower) for genre in ['jazz', 'prog', 'soul', 'funk']):
            genre_multiplier = 1.8
        elif any(genre in ' '.join(genres_lower) for genre in ['classical', 'electronic', 'ambient']):
            genre_multiplier = 1.4
        elif any(genre in ' '.join(genres_lower) for genre in ['rock', 'pop']):
            genre_multiplier = 1.0

    # Catalog number rarity multiplier
    # Longer, more specific catalog numbers suggest rarer/special editions
    catalog_multiplier = 1.0
    if catalog_number:
        # Check if catalog number is substantial (more than just a few chars)
        if len(catalog_number.strip()) > 4:
            catalog_multiplier = 1.2  # Specific editions tend to be worth slightly more
        elif len(catalog_number.strip()) > 2:
            catalog_multiplier = 1.1

    # Condition multiplier (if provided)
    # Condition score: 0.0 (poor) to 1.0 (mint)
    # Formula: 0.4 (poor) to 1.5 (mint)
    condition_multiplier = 1.0
    if condition_score is not None:
        # Map condition_score (0.0-1.0) to multiplier (0.4-1.5)
        condition_multiplier = 0.4 + (condition_score * 1.1)

    # Calculate final values
    estimated_eur = (base_value_eur * year_multiplier * label_multiplier * 
                     genre_multiplier * catalog_multiplier * condition_multiplier)

    # Cap values between €5 and €500 (realistic for common vinyl)
    estimated_eur = max(5.0, min(500.0, estimated_eur))
    estimated_usd = estimated_eur / 0.92  # Rough EUR to USD conversion

    logger.debug(
        f"Value estimate for {artist} - {title}: "
        f"€{estimated_eur:.2f} (multipliers: year={year_multiplier:.2f}, "
        f"label={label_multiplier:.2f}, genre={genre_multiplier:.2f}, "
        f"catalog={catalog_multiplier:.2f}, condition={condition_multiplier:.2f})"
    )

    return {
        "estimated_value_eur": round(estimated_eur, 2),
        "estimated_value_usd": round(estimated_usd, 2),
    }
