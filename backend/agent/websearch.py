"""
Tavily-powered websearch fallback for vinyl record metadata.

This module provides fallback search functionality when primary metadata sources
(Discogs, MusicBrainz) have insufficient confidence. Uses Tavily API for web search.

Cost: ~$0.0005 per search (Tavily pricing)
Triggered when: Primary source confidence < 0.75
"""

import logging
import os
from typing import Optional, Dict, List, Any

from tavily import TavilyClient
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

logger = logging.getLogger(__name__)

# Search tuning – all values can be overridden via environment variables
# Minimum number of Tavily results before DuckDuckGo is used to supplement
MIN_RESULTS_THRESHOLD = int(os.getenv("WEBSEARCH_MIN_RESULTS_THRESHOLD", "4"))
# Maximum results fetched per Tavily / DuckDuckGo call
WEBSEARCH_MAX_RESULTS = int(os.getenv("WEBSEARCH_MAX_RESULTS", "7"))
# Maximum results returned from barcode searches
WEBSEARCH_BARCODE_MAX_RESULTS = int(os.getenv("WEBSEARCH_BARCODE_MAX_RESULTS", "5"))


class WebsearchError(Exception):
    """Raised when websearch operation fails."""

    pass


def search_vinyl_metadata(
    artist: str,
    title: str,
    fallback_on_error: bool = True,
) -> List[Dict[str, Any]]:
    """
    Search for vinyl record metadata using Tavily API with DuckDuckGo fallback.

    Args:
        artist: Artist or group name
        title: Album title
        fallback_on_error: If True, return empty list on API error; if False, raise exception

    Returns:
        List of search results, each with:
        - title: Result title
        - url: Result URL
        - snippet: Result snippet/description
        - relevance: Relevance score (0.0-1.0)

    Raises:
        WebsearchError: If search fails and fallback_on_error=False
    """
    if not artist or not title:
        raise ValueError("Artist and title are required")

    # Construct search query
    search_query = f"{artist} {title} vinyl record album"

    tavily_results: List[Dict[str, Any]] = []

    # Try Tavily first
    try:
        logger.info(f"Searching Tavily for: {search_query}")
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

        response: Dict[str, Any] = client.search(
            query=search_query,
            include_images=False,
            max_results=WEBSEARCH_MAX_RESULTS,
        )

        # Parse Tavily response
        tavily_results = _parse_tavily_response(response)
        if len(tavily_results) >= MIN_RESULTS_THRESHOLD:
            logger.info(f"Found {len(tavily_results)} search results via Tavily")
            return tavily_results
        elif tavily_results:
            logger.info(
                f"Tavily returned only {len(tavily_results)} result(s) "
                f"(< {MIN_RESULTS_THRESHOLD}), supplementing with DuckDuckGo"
            )
        else:
            logger.info("Tavily returned no results, trying DuckDuckGo")

    except Exception as e:
        logger.warning(f"Tavily search failed: {e}, trying DuckDuckGo fallback")

    # Supplement or replace with DuckDuckGo when Tavily results < MIN_RESULTS_THRESHOLD
    try:
        ddg_results = _duckduckgo_search(search_query, max_results=WEBSEARCH_MAX_RESULTS)
        combined = _deduplicate_results(tavily_results + ddg_results)
        if combined:
            logger.info(
                f"Combined results: {len(tavily_results)} Tavily + "
                f"{len(ddg_results)} DuckDuckGo = {len(combined)} unique"
            )
            return combined[:WEBSEARCH_MAX_RESULTS]
        elif tavily_results:
            logger.warning("DuckDuckGo returned no results; returning sparse Tavily results")
            return tavily_results
        else:
            logger.warning("Both Tavily and DuckDuckGo returned no results")

    except Exception as e:
        logger.error(f"DuckDuckGo also failed: {e}")
        if tavily_results:
            return tavily_results

    # If we get here, all searches failed
    if fallback_on_error:
        logger.warning("Returning empty results due to all search methods failing")
        return []
    else:
        raise WebsearchError(f"Websearch failed: Tavily and DuckDuckGo both unavailable")


def search_vinyl_by_barcode(
    barcode: str,
    artist: Optional[str] = None,
    title: Optional[str] = None,
    fallback_on_error: bool = True,
) -> List[Dict[str, Any]]:
    """
    Search for vinyl record information using barcode/UPC with fallback to DuckDuckGo.

    Args:
        barcode: UPC/EAN barcode number (12-13 digits)
        artist: Optional artist name for additional context
        title: Optional album title for additional context
        fallback_on_error: If True, return empty list on API error; if False, raise exception

    Returns:
        List of search results with barcode-specific information

    Raises:
        WebsearchError: If search fails and fallback_on_error=False
    """
    if not barcode or not barcode.strip():
        raise ValueError("Barcode is required")

    # Clean and validate barcode
    clean_barcode = barcode.strip().replace(" ", "").replace("-", "")
    
    # Basic barcode validation (12-13 digits)
    if not clean_barcode.isdigit() or len(clean_barcode) not in [12, 13]:
        logger.warning(f"Invalid barcode format: {barcode} (cleaned: {clean_barcode})")
        if fallback_on_error:
            return []
        else:
            raise ValueError(f"Invalid barcode format: {barcode}")

    # Construct barcode-focused search queries
    search_queries = [
        f"UPC {clean_barcode} vinyl record album",
        f"barcode {clean_barcode} vinyl LP",
    ]
    
    # Add context-specific queries if artist/title provided
    if artist and title:
        search_queries.insert(0, f'"{artist}" "{title}" UPC {clean_barcode} vinyl')
    elif artist:
        search_queries.insert(0, f'"{artist}" UPC {clean_barcode} vinyl album')
    elif title:
        search_queries.insert(0, f'"{title}" UPC {clean_barcode} vinyl record')

    all_results = []
    
    # Try Tavily first
    try:
        logger.info(f"Trying Tavily barcode search for: {clean_barcode}")
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        
        for i, query in enumerate(search_queries[:2]):  # Limit to 2 searches to control costs
            logger.info(f"Tavily barcode search {i+1}: {query}")
            
            try:
                response: Dict[str, Any] = client.search(
                    query=query,
                    include_images=False,
                    max_results=WEBSEARCH_MAX_RESULTS,
                )
                
                results = _parse_tavily_response(response)
                all_results.extend(results)
                logger.info(f"Tavily barcode search {i+1} found {len(results)} results")
                
            except Exception as e:
                logger.warning(f"Tavily barcode search {i+1} failed: {e}")
                continue
        
        tavily_unique = _deduplicate_results(all_results)
        if len(tavily_unique) >= MIN_RESULTS_THRESHOLD:
            logger.info(f"Found {len(tavily_unique)} unique barcode search results via Tavily")
            return tavily_unique[:WEBSEARCH_BARCODE_MAX_RESULTS]
        elif tavily_unique:
            logger.info(
                f"Tavily returned only {len(tavily_unique)} barcode result(s) "
                f"(< {MIN_RESULTS_THRESHOLD}), supplementing with DuckDuckGo"
            )
            all_results = tavily_unique  # keep for merging below

    except Exception as e:
        logger.warning(f"Tavily barcode search failed: {e}, trying DuckDuckGo fallback")

    # Supplement or replace with DuckDuckGo when Tavily results < MIN_RESULTS_THRESHOLD
    try:
        logger.info(f"Trying DuckDuckGo barcode search for: {clean_barcode}")
        for query in search_queries[:2]:
            logger.info(f"DuckDuckGo barcode search: {query}")

            try:
                ddg_results = _duckduckgo_search(query, max_results=WEBSEARCH_MAX_RESULTS)
                all_results.extend(ddg_results)
                logger.info(f"DuckDuckGo barcode search found {len(ddg_results)} results")
            except Exception as e:
                logger.warning(f"DuckDuckGo barcode search failed: {e}")
                continue

        combined = _deduplicate_results(all_results)
        if combined:
            logger.info(f"Found {len(combined)} unique barcode search results (Tavily + DuckDuckGo)")
            return combined[:WEBSEARCH_BARCODE_MAX_RESULTS]

    except Exception as e:
        logger.error(f"DuckDuckGo barcode search also failed: {e}")
        if all_results:
            return _deduplicate_results(all_results)[:WEBSEARCH_BARCODE_MAX_RESULTS]

    # If we get here, both search methods failed
    logger.error(f"Barcode search failed for {clean_barcode} (both Tavily and DuckDuckGo)")
    if fallback_on_error:
        logger.warning("Returning empty results due to all search methods failing")
        return []
    else:
        raise WebsearchError(f"Barcode search failed: both Tavily and DuckDuckGo unavailable")


def _parse_tavily_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse Tavily API response into standardized format.

    Args:
        response: Dictionary response from Tavily API

    Returns:
        List of standardized result dictionaries
    """
    results: List[Dict[str, Any]] = []

    if not response or not isinstance(response, dict):
        logger.warning("Invalid Tavily response structure")
        return results

    # Tavily returns results in "results" key
    tavily_results = response.get("results", [])
    
    if not tavily_results:
        logger.warning("No results in Tavily response")
        return results

    for idx, result in enumerate(tavily_results):
        # Extract fields from Tavily result dict
        parsed_result: Dict[str, Any] = {
            "title": result.get("title", f"Result {idx + 1}"),
            "url": result.get("url", ""),
            "snippet": result.get("content", ""),
            "relevance": _calculate_relevance(result.get("url", "")),
        }
        results.append(parsed_result)

    return results


def _deduplicate_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate results by URL, preserving order.
    Results with empty/missing URLs are kept only once.
    """
    seen: set = set()
    deduped: List[Dict[str, Any]] = []
    for result in results:
        url = result.get("url", "")
        if url and url not in seen:
            seen.add(url)
            deduped.append(result)
    return deduped


def _duckduckgo_search(query: str, max_results: int = 7) -> List[Dict[str, Any]]:
    """
    Fallback web search using DuckDuckGo Search API (via duckduckgo-search library).
    
    This library handles DuckDuckGo's anti-bot measures and rate limiting gracefully.

    Args:
        query: Search query string
        max_results: Maximum number of results to return

    Returns:
        List of search results in standard format or empty list if search fails
    """
    try:
        logger.info(f"DuckDuckGo fallback search for: {query}")
        
        ddgs = DDGS(timeout=10)
        ddg_results = list(ddgs.text(query, max_results=max_results))
        
        if not ddg_results:
            logger.warning("DuckDuckGo returned no results")
            return []
        
        results: List[Dict[str, Any]] = []
        for result in ddg_results:
            parsed_result: Dict[str, Any] = {
                "title": result.get("title", ""),
                "url": result.get("href", ""),
                "snippet": result.get("body", ""),
                "relevance": _calculate_relevance(result.get("href", "")),
            }
            results.append(parsed_result)

        logger.info(f"DuckDuckGo returned {len(results)} results")
        return results

    except Exception as e:
        logger.warning(f"DuckDuckGo fallback search failed: {type(e).__name__}: {e}")
        return []


def _calculate_relevance(result: Any) -> float:
    """
    Calculate relevance score for a search result.

    Heuristics:
    - Discogs URLs: 0.95
    - MusicBrainz URLs: 0.90
    - Wikipedia: 0.70
    - Generic: 0.50

    Args:
        result: URL string or dict with URL

    Returns:
        Relevance score (0.0-1.0)
    """
    # Handle dict results (from parsed response)
    if isinstance(result, dict):
        url = result.get("url", "").lower()
    else:
        # Handle string URLs directly
        url = str(result).lower()

    if "discogs.com" in url:
        return 0.95
    elif "musicbrainz.org" in url:
        return 0.90
    elif "wikipedia.org" in url:
        return 0.70
    elif "vinyl" in url or "record" in url:
        return 0.65
    else:
        return 0.50


def search_vinyl_metadata_with_fallback(
    artist: str,
    title: str,
    max_retries: int = 1,
) -> Dict[str, Any]:
    """
    Search for vinyl metadata with retry logic and fallback.

    Args:
        artist: Artist or group name
        title: Album title
        max_retries: Number of retries on error (default: 1)

    Returns:
        Dict with keys:
        - results: List of search results
        - success: Whether search succeeded
        - error: Error message if failed
        - query: The search query used
    """
    results = []
    error_msg = None

    for attempt in range(max_retries + 1):
        try:
            results = search_vinyl_metadata(
                artist=artist,
                title=title,
                fallback_on_error=True,
            )
            if results:
                break
            elif attempt < max_retries:
                logger.warning(f"No results, retrying (attempt {attempt + 1}/{max_retries})")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Search attempt {attempt + 1} failed: {e}")

    return {
        "results": results,
        "success": len(results) > 0,
        "error": error_msg,
        "query": f"{artist} {title}",
    }


def search_spotify_album(
    artist: str,
    title: str,
    fallback_on_error: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Search for Spotify album link using Tavily websearch with DuckDuckGo fallback.

    Args:
        artist: Artist or group name
        title: Album title
        fallback_on_error: If True, return None on error; if False, raise exception

    Returns:
        Dictionary with:
        - spotify_url: Direct Spotify album URL
        - artist: Artist name
        - title: Album title
        - source: "spotify"

    Raises:
        WebsearchError: If search fails and fallback_on_error=False
    """
    if not artist or not title:
        logger.warning("Artist and title are required for Spotify search")
        return None

    # Try Tavily first with site restriction
    try:
        logger.info(f"Searching Spotify (Tavily) for: {artist} - {title}")
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        search_query = f"{artist} {title} album site:spotify.com"

        response: Dict[str, Any] = client.search(
            query=search_query,
            include_images=False,
            max_results=7,
        )

        # Look for Spotify URL in results
        if response.get("results"):
            for result in response["results"]:
                url = result.get("url", "")
                if "spotify.com/album/" in url:
                    logger.info(f"Found Spotify album (Tavily): {url}")
                    return {
                        "spotify_url": url,
                        "artist": artist,
                        "title": title,
                        "source": "spotify",
                    }

        logger.info("No site-restricted Spotify result found via Tavily, trying DuckDuckGo fallback")

    except Exception as e:
        logger.warning(f"Tavily Spotify search failed: {e}, trying DuckDuckGo fallback")

    # Try DuckDuckGo as fallback
    try:
        # Include site: operator so DuckDuckGo also focuses on Spotify album pages
        search_query = f"{artist} {title} album site:open.spotify.com"
        ddg_results = _duckduckgo_search(search_query, max_results=7)
        
        for result in ddg_results:
            url = result.get("url", "")
            if "spotify.com/album/" in url:
                logger.info(f"Found Spotify album (DuckDuckGo): {url}")
                return {
                    "spotify_url": url,
                    "artist": artist,
                    "title": title,
                    "source": "spotify",
                }
        
        # If site-restricted query found nothing, try a broader fallback
        logger.info("DuckDuckGo site-restricted search returned no album, trying broader query")
        search_query_broad = f"{artist} {title} spotify album"
        ddg_results_broad = _duckduckgo_search(search_query_broad, max_results=10)
        
        for result in ddg_results_broad:
            url = result.get("url", "")
            if "spotify.com/album/" in url:
                logger.info(f"Found Spotify album (DuckDuckGo broad): {url}")
                return {
                    "spotify_url": url,
                    "artist": artist,
                    "title": title,
                    "source": "spotify",
                }

        logger.warning(f"No Spotify album found via Tavily or DuckDuckGo for {artist} - {title}")
        return None

    except Exception as e:
        logger.error(f"Spotify search failed (both Tavily and DuckDuckGo): {e}")
        if fallback_on_error:
            return None
        else:
            raise WebsearchError(f"Spotify search failed: {e}") from e
