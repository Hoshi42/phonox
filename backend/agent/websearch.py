"""
Tavily-powered websearch fallback for vinyl record metadata.

This module provides fallback search functionality when primary metadata sources
(Discogs, MusicBrainz) have insufficient confidence. Uses Tavily API for web search.

Cost: ~$0.0005 per search (Tavily pricing)
Triggered when: Primary source confidence < 0.75
"""

import logging
from typing import Optional, Dict, List, Any

from tavily import TavilyClient

logger = logging.getLogger(__name__)


class WebsearchError(Exception):
    """Raised when websearch operation fails."""

    pass


def search_vinyl_metadata(
    artist: str,
    title: str,
    fallback_on_error: bool = True,
) -> List[Dict[str, Any]]:
    """
    Search for vinyl record metadata using Tavily API.

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

    client = TavilyClient()

    # Construct search query
    search_query = f"{artist} {title} vinyl record album"

    try:
        logger.info(f"Searching Tavily for: {search_query}")

        response: Dict[str, Any] = client.search(
            query=search_query,
            include_images=False,
            max_results=5,
        )

        # Parse Tavily response
        results = _parse_tavily_response(response)
        logger.info(f"Found {len(results)} search results")

        return results

    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        if fallback_on_error:
            logger.warning("Returning empty results due to error")
            return []
        else:
            raise WebsearchError(f"Websearch failed: {e}") from e


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
