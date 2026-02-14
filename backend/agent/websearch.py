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

    # Try Tavily first
    try:
        logger.info(f"Searching Tavily for: {search_query}")
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

        response: Dict[str, Any] = client.search(
            query=search_query,
            include_images=False,
            max_results=7,
        )

        # Parse Tavily response
        results = _parse_tavily_response(response)
        if results:
            logger.info(f"Found {len(results)} search results via Tavily")
            return results
        else:
            logger.info("Tavily returned no results, trying DuckDuckGo fallback")

    except Exception as e:
        logger.warning(f"Tavily search failed: {e}, trying DuckDuckGo fallback")

    # Fallback to DuckDuckGo
    try:
        ddg_results = _duckduckgo_search(search_query, max_results=7)
        if ddg_results:
            logger.info(f"Found {len(ddg_results)} search results via DuckDuckGo")
            return ddg_results
        else:
            logger.warning("Both Tavily and DuckDuckGo returned no results")
            
    except Exception as e:
        logger.error(f"DuckDuckGo fallback also failed: {e}")

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
                    max_results=7,
                )
                
                results = _parse_tavily_response(response)
                all_results.extend(results)
                logger.info(f"Tavily barcode search {i+1} found {len(results)} results")
                
            except Exception as e:
                logger.warning(f"Tavily barcode search {i+1} failed: {e}")
                continue
        
        if all_results:
            # Return Tavily results
            seen_urls = set()
            unique_results = []
            for result in all_results:
                url = result.get('url', '')
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(result)
            
            logger.info(f"Found {len(unique_results)} unique barcode search results via Tavily")
            return unique_results[:5]

    except Exception as e:
        logger.warning(f"Tavily barcode search failed: {e}, trying DuckDuckGo fallback")

    # Fallback to DuckDuckGo
    try:
        logger.info(f"Trying DuckDuckGo barcode search for: {clean_barcode}")
        for query in search_queries[:2]:
            logger.info(f"DuckDuckGo barcode search: {query}")
            
            try:
                ddg_results = _duckduckgo_search(query, max_results=7)
                all_results.extend(ddg_results)
                logger.info(f"DuckDuckGo barcode search found {len(ddg_results)} results")
            except Exception as e:
                logger.warning(f"DuckDuckGo barcode search failed: {e}")
                continue

        if all_results:
            # Deduplicate and return
            seen_urls = set()
            unique_results = []
            for result in all_results:
                url = result.get('url', '')
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(result)
            
            logger.info(f"Found {len(unique_results)} unique barcode search results via DuckDuckGo")
            return unique_results[:5]

    except Exception as e:
        logger.error(f"DuckDuckGo barcode search also failed: {e}")

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


def _duckduckgo_search(query: str, max_results: int = 7) -> List[Dict[str, Any]]:
    """
    Fallback web search using DuckDuckGo HTML search (no API key required).

    Args:
        query: Search query string
        max_results: Maximum number of results to return

    Returns:
        List of search results in standard format
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        params = {
            'q': query,
            'kl': 'us-en',
            'ia': 'web'
        }

        logger.info(f"DuckDuckGo fallback search for: {query}")
        resp = requests.get('https://duckduckgo.com/html/', params=params, headers=headers, timeout=10)
        resp.raise_for_status()

        try:
            soup = BeautifulSoup(resp.text, 'html.parser')
            results: List[Dict[str, Any]] = []

            for result in soup.select('.result__body')[:max_results]:
                link = result.select_one('a.result__a')
                snippet_elem = result.select_one('.result__snippet')
                if not link:
                    continue

                href = link.get('href')
                title = link.get_text(strip=True)
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''

                parsed_result: Dict[str, Any] = {
                    "title": title,
                    "url": href,
                    "snippet": snippet,
                    "relevance": _calculate_relevance(href),
                }
                results.append(parsed_result)

            logger.info(f"DuckDuckGo returned {len(results)} results")
            return results
        finally:
            resp.close()

    except Exception as e:
        logger.error(f"DuckDuckGo fallback search failed: {e}")
        return []


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

        logger.info("No site-restricted Spotify result found, trying broader Tavily search")

    except Exception as e:
        logger.warning(f"Tavily Spotify search failed: {e}, trying DuckDuckGo fallback")

    # Try DuckDuckGo as fallback
    try:
        search_query = f"{artist} {title} spotify album"
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

        logger.warning(f"No Spotify album found via Tavily or DuckDuckGo for {artist} - {title}")
        return None

    except Exception as e:
        logger.error(f"Spotify search failed (both Tavily and DuckDuckGo): {e}")
        if fallback_on_error:
            return None
        else:
            raise WebsearchError(f"Spotify search failed: {e}") from e
