"""
Metadata lookup module for Discogs and MusicBrainz APIs.

This module provides vinyl record metadata lookups from two major music databases:
- Discogs: Extensive discography with vinyl-specific data
- MusicBrainz: Community-driven music metadata

Cost: Free (both APIs are free to use)
Note: Requires internet connectivity; handles timeouts gracefully
"""

import difflib
import logging
import os
import re
import requests
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import quote

logger = logging.getLogger(__name__)

# API endpoints
DISCOGS_API_BASE = "https://api.discogs.com"


def _discogs_headers() -> Dict[str, str]:
    """Build Discogs request headers. Adds auth token if DISCOGS_TOKEN is set."""
    headers = {
        "User-Agent": "Phonox/1.0 (vinyl identification app; contact: https://github.com/hoshhie/phonox)"
    }
    token = os.getenv("DISCOGS_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Discogs token={token}"
    return headers
MUSICBRAINZ_API_BASE = "https://musicbrainz.org/ws/2"

# Headers for MusicBrainz API (required)
MUSICBRAINZ_HEADERS = {
    "User-Agent": "Phonox/1.0 (https://github.com/hoshhie/phonox)",
    "Accept": "application/json",
}

# Timeout for API calls
API_TIMEOUT = 5  # seconds

# Number of Discogs search hits ranked when looking for the exact pressing
DISCOGS_CANDIDATES = 25


def musicbrainz_enabled() -> bool:
    """MusicBrainz is opt-in: its public endpoint answers 503 intermittently."""
    return os.getenv("MUSICBRAINZ_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")


class MetadataError(Exception):
    """Raised when metadata lookup fails."""

    pass


def _normalize_catno(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _normalize_barcode(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _discogs_search(params: Dict[str, str]) -> List[Dict[str, Any]]:
    """Run one Discogs database search and return its result list."""
    response = requests.get(
        f"{DISCOGS_API_BASE}/database/search",
        params={"type": "release", "per_page": str(DISCOGS_CANDIDATES), **params},
        timeout=API_TIMEOUT,
        headers=_discogs_headers(),
    )
    response.raise_for_status()
    try:
        data = response.json()
    finally:
        response.close()
    return data.get("results", [])


def _score_discogs_candidate(
    candidate: Dict[str, Any],
    artist: str,
    title: str,
    catalog_number: Optional[str],
    barcode: Optional[str],
    year: Optional[int],
    label: Optional[str],
) -> Tuple[float, Optional[str]]:
    """
    Score one Discogs search hit against what was read from the record.

    Returns (score, exact_basis) where exact_basis is "catalog_number" or
    "barcode" when that identifier matches the hit exactly, otherwise None.
    """
    score = 0.0
    basis: Optional[str] = None

    wanted_catno = _normalize_catno(catalog_number)
    if wanted_catno and wanted_catno == _normalize_catno(candidate.get("catno")):
        score += 100
        basis = "catalog_number"

    wanted_barcode = _normalize_barcode(barcode)
    if len(wanted_barcode) >= 8:
        candidate_barcodes = {_normalize_barcode(b) for b in candidate.get("barcode") or []}
        if wanted_barcode in candidate_barcodes:
            score += 100
            basis = basis or "barcode"

    formats = " ".join(str(f) for f in candidate.get("format") or []).lower()
    if "vinyl" in formats:
        score += 10
        if "lp" in formats:
            score += 5
    elif formats:
        score -= 20
    if "unofficial" in formats:
        score -= 15

    if year and str(candidate.get("year") or "") == str(year):
        score += 15

    # Several Discogs entries often describe the same pressing; prefer the most-owned one
    have = (candidate.get("community") or {}).get("have") or 0
    score += 3 * min(have, 2000) / 2000

    wanted_label = (label or "").lower()
    if wanted_label and any(
        wanted_label in str(name).lower() or str(name).lower() in wanted_label
        for name in candidate.get("label") or []
    ):
        score += 10

    candidate_title = str(candidate.get("title") or "").lower()
    score += 20 * difflib.SequenceMatcher(None, candidate_title, f"{artist} - {title}".lower()).ratio()

    return score, basis


def _find_discogs_release(
    artist: str,
    title: str,
    catalog_number: Optional[str],
    barcode: Optional[str],
    year: Optional[int],
    label: Optional[str],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Find the best Discogs release, preferring the exact pressing.

    Searches by catalog number, then barcode, then artist/title, and stops as
    soon as a hit matches an identifier exactly.
    """
    searches: List[Dict[str, str]] = []
    if catalog_number and _normalize_catno(catalog_number):
        searches.append({"catno": catalog_number, "artist": artist})
    if len(_normalize_barcode(barcode)) >= 8:
        searches.append({"barcode": _normalize_barcode(barcode)})
    if title:
        searches.append({"artist": artist, "release_title": title})

    seen: Dict[Any, Tuple[float, Optional[str], Dict[str, Any]]] = {}
    last_error: Optional[Exception] = None
    for params in searches:
        try:
            results = _discogs_search(params)
        except Exception as e:
            last_error = e
            logger.warning(f"Discogs search {list(params)} failed: {e}")
            continue

        exact_found = False
        for hit in results:
            if not hit.get("id") or hit["id"] in seen:
                continue
            score, basis = _score_discogs_candidate(hit, artist, title, catalog_number, barcode, year, label)
            seen[hit["id"]] = (score, basis, hit)
            exact_found = exact_found or basis is not None
        if exact_found:
            break

    if not seen:
        if last_error:
            raise last_error
        return None, None
    _, basis, best = max(seen.values(), key=lambda item: item[0])
    return best, basis


def _extract_discogs_market(release_data: Dict[str, Any]) -> Dict[str, Any]:
    """Marketplace and community figures from a Discogs release (priced in EUR)."""
    community = release_data.get("community") or {}
    rating = community.get("rating") or {}
    lowest = release_data.get("lowest_price")
    return {
        "currency": "EUR",
        "lowest_price": float(lowest) if isinstance(lowest, (int, float)) else None,
        "num_for_sale": release_data.get("num_for_sale"),
        "have": community.get("have"),
        "want": community.get("want"),
        "rating_average": rating.get("average"),
        "price_suggestions": None,
    }


def _fetch_discogs_price_suggestions(release_id: Any) -> Optional[Dict[str, float]]:
    """Per-condition price suggestions. Needs a token and filled-out Discogs seller settings."""
    if not os.getenv("DISCOGS_TOKEN", "").strip():
        return None
    try:
        response = requests.get(
            f"{DISCOGS_API_BASE}/marketplace/price_suggestions/{release_id}",
            timeout=API_TIMEOUT,
            headers=_discogs_headers(),
        )
        if response.status_code != 200:
            logger.info(f"Discogs price suggestions unavailable (HTTP {response.status_code})")
            return None
        try:
            data = response.json()
        finally:
            response.close()
        return {
            condition: round(float(entry["value"]), 2)
            for condition, entry in data.items()
            if isinstance(entry, dict) and entry.get("value") is not None
        } or None
    except Exception as e:
        logger.info(f"Discogs price suggestions failed: {e}")
        return None


def format_discogs_market_context(discogs: Optional[Dict[str, Any]]) -> str:
    """Describe Discogs pressing and marketplace data for a valuation prompt."""
    if not discogs or not discogs.get("discogs_release_id"):
        return ""
    market = discogs.get("marketplace") or {}
    pressing = "EXACT pressing (catalog number/barcode matched)" if discogs.get("exact_match") else (
        "closest release by artist/title (pressing NOT confirmed)"
    )
    lines = [
        f"Discogs release {discogs['discogs_release_id']}: {pressing}",
        f"- Release: {discogs.get('artist')} - {discogs.get('title')}, {discogs.get('year') or 'year unknown'}, "
        f"{discogs.get('label') or 'label unknown'}, cat# {discogs.get('catalog_number') or 'unknown'}, "
        f"{discogs.get('country') or 'country unknown'}, {discogs.get('format') or 'format unknown'}",
    ]
    if market.get("lowest_price") is not None:
        lines.append(
            f"- Lowest price currently listed on Discogs: €{market['lowest_price']:.2f} "
            f"({market.get('num_for_sale') or 0} copies for sale)"
        )
    elif market.get("num_for_sale") == 0:
        lines.append("- No copies currently for sale on Discogs")
    if market.get("have") is not None:
        lines.append(f"- Collection/wantlist: {market.get('have')} have, {market.get('want')} want")
    if market.get("price_suggestions"):
        suggestions = ", ".join(f"{cond}: €{value:.2f}" for cond, value in market["price_suggestions"].items())
        lines.append(f"- Discogs price suggestions by condition: {suggestions}")
    if discogs.get("discogs_url"):
        lines.append(f"- URL: {discogs['discogs_url']}")
    return "\n".join(lines)


def lookup_discogs_metadata(
    artist: str,
    title: str,
    fallback_on_error: bool = True,
    catalog_number: Optional[str] = None,
    barcode: Optional[str] = None,
    year: Optional[int] = None,
    label: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Lookup vinyl record metadata from Discogs API.

    When a catalog number or barcode is given, the exact pressing is searched
    first; otherwise (or if nothing matches) the best artist/title hit is used.
    The release's marketplace figures are returned under "marketplace".

    Args:
        artist: Artist or group name
        title: Album/release title
        fallback_on_error: If True, return None on error; if False, raise exception
        catalog_number: Catalog number read from the record (optional)
        barcode: Barcode read from the record (optional)
        year: Release year read from the record (optional)
        label: Label read from the record (optional)

    Returns:
        Dict with keys: artist, title, year, label, catalog_number, genres, confidence,
        discogs_release_id, discogs_url, country, format, exact_match, match_basis, marketplace.
        Returns None if not found or error occurred

    Raises:
        MetadataError: If lookup fails and fallback_on_error=False
    """
    if not artist:
        raise ValueError("Artist and title are required")
    if not title and not (_normalize_catno(catalog_number) or len(_normalize_barcode(barcode)) >= 8):
        raise ValueError("Artist and title are required")

    try:
        logger.info(
            f"Discogs lookup: {artist} - {title} "
            f"(cat#: {catalog_number or '-'}, barcode: {barcode or '-'}, year: {year or '-'})"
        )

        release, match_basis = _find_discogs_release(artist, title, catalog_number, barcode, year, label)
        if not release:
            logger.warning(f"Discogs: No results for {artist} - {title}")
            return None

        release_id = release.get("id")

        # Fetch detailed release information (marketplace figures priced in EUR)
        release_url = f"{DISCOGS_API_BASE}/releases/{release_id}"
        detail_response = requests.get(
            release_url,
            params={"curr_abbr": "EUR"},
            timeout=API_TIMEOUT,
            headers=_discogs_headers(),
        )
        detail_response.raise_for_status()

        try:
            release_data = detail_response.json()
        finally:
            # Always close connection to free resources
            detail_response.close()

        catalog = _extract_discogs_catalog(release_data)
        if not match_basis and catalog_number and any(
            _normalize_catno(item.get("catno")) == _normalize_catno(catalog_number)
            for item in release_data.get("labels") or []
        ):
            match_basis = "catalog_number"

        market = _extract_discogs_market(release_data)
        market["price_suggestions"] = _fetch_discogs_price_suggestions(release_id)
        formats = release_data.get("formats") or []
        format_text = ", ".join(
            [str(formats[0].get("name"))] + [str(d) for d in formats[0].get("descriptions", [])]
        ) if formats and formats[0].get("name") else None

        # Extract metadata
        metadata = {
            "artist": _extract_discogs_artist(release_data),
            "title": release_data.get("title", title),
            "year": release_data.get("year"),
            "label": _extract_discogs_label(release_data),
            "catalog_number": catalog,
            "genres": release_data.get("genres", []),
            "confidence": 0.92 if match_basis else 0.85,  # An identifier match confirms the pressing
            "discogs_release_id": release_id,
            "discogs_url": release_data.get("uri") or f"https://www.discogs.com/release/{release_id}",
            "country": release_data.get("country"),
            "format": format_text,
            "exact_match": match_basis is not None,
            "match_basis": match_basis or "artist_title",
            "marketplace": market,
        }

        logger.info(
            f"Discogs: Found {metadata['artist']} - {metadata['title']} "
            f"(release {release_id}, match: {metadata['match_basis']}, cat# {catalog}, "
            f"lowest €{market['lowest_price']}, {market['num_for_sale']} for sale)"
        )
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

    if not musicbrainz_enabled():
        logger.debug("MusicBrainz lookup skipped (set MUSICBRAINZ_ENABLED=true to enable)")
        return None

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

        try:
            data = response.json()
        finally:
            # Always close connection to free resources
            response.close()
        
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
    catalog_number: Optional[str] = None,
    barcode: Optional[str] = None,
    year: Optional[int] = None,
    label: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Lookup metadata from Discogs and (if enabled) MusicBrainz.

    Discogs is queried unauthenticated (25 req/min) or with a token if
    DISCOGS_TOKEN is set in the environment (60 req/min). The optional
    catalog number, barcode, year and label narrow Discogs down to the exact
    pressing. MusicBrainz is skipped unless MUSICBRAINZ_ENABLED is true.

    Args:
        artist: Artist or group name
        title: Album/release title
        catalog_number: Catalog number read from the record (optional)
        barcode: Barcode read from the record (optional)
        year: Release year read from the record (optional)
        label: Label read from the record (optional)

    Returns:
        Tuple of (discogs_result, musicbrainz_result)
    """
    discogs_result = lookup_discogs_metadata(
        artist,
        title,
        fallback_on_error=True,
        catalog_number=catalog_number,
        barcode=barcode,
        year=year,
        label=label,
    )
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
