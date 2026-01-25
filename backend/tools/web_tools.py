"""Web search and scraping tools for enhanced chatbot functionality."""

import logging
import os
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient

logger = logging.getLogger(__name__)

class WebSearchTool:
    """Web search tool using Tavily API."""
    
    def __init__(self):
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not self.tavily_api_key:
            logger.warning("TAVILY_API_KEY not found in environment")
            self.client = None
        else:
            self.client = TavilyClient(api_key=self.tavily_api_key)
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search the web using Tavily API."""
        results: List[Dict[str, Any]] = []

        # Primary: Tavily (if configured)
        if self.client:
            try:
                logger.info(f"Searching web via Tavily for: {query}")
                response = self.client.search(
                    query=query,
                    search_depth="basic",
                    max_results=max_results,
                    include_domains=["discogs.com", "musicbrainz.org", "allmusic.com", "wikipedia.org"],
                    exclude_domains=["ebay.com", "amazon.com"]  # Exclude marketplaces for cleaner results
                )

                for result in response.get("results", []):
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": result.get("content", ""),
                        "score": result.get("score", 0.0)
                    })

            except Exception as e:
                logger.error(f"Error searching Tavily: {e}")

        # Secondary: DuckDuckGo HTML search (no API key required)
        try:
            ddg_results = self._duckduckgo_search(query, max_results=max_results)
            results.extend(ddg_results)
        except Exception as e:
            logger.error(f"Error searching DuckDuckGo: {e}")

        # Deduplicate by URL while preserving order
        seen = set()
        deduped = []
        for r in results:
            url = r.get("url") or r.get("href") or ""
            if url and url not in seen:
                seen.add(url)
                deduped.append(r)

        # Fallback if everything failed
        if not deduped:
            return [{
                "title": "Search unavailable",
                "url": "#",
                "content": "Web search is not configured or failed. Please set TAVILY_API_KEY or check network.",
                "score": 0.0
            }]

        # Limit to max_results combined
        return deduped[:max_results]
    
    def search_vinyl_info(self, artist: str, title: str) -> List[Dict[str, Any]]:
        """Search for specific vinyl record information."""
        query = f"{artist} {title} vinyl record discography information"
        return self.search(query, max_results=3)
    
    def search_vinyl_prices(self, artist: str, title: str) -> List[Dict[str, Any]]:
        """Search for vinyl record pricing information."""
        query = f"{artist} {title} vinyl record value price market"
        return self.search(query, max_results=4)

    def _duckduckgo_search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Lightweight DuckDuckGo HTML search (no API key)."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        params = {
            'q': query,
            'kl': 'us-en',
            'ia': 'web'
        }

        resp = requests.get('https://duckduckgo.com/html/', params=params, headers=headers, timeout=10)
        resp.raise_for_status()

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

            results.append({
                "title": title,
                "url": href,
                "content": snippet,
                "score": 0.0  # DuckDuckGo HTML does not provide score
            })

        logger.info(f"DuckDuckGo returned {len(results)} results for: {query}")
        return results


class WebScrapingTool:
    """Web scraping tool for extracting content from URLs."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def scrape_url(self, url: str, max_chars: int = 2000) -> Dict[str, Any]:
        """Scrape content from a URL."""
        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return {
                    "success": False,
                    "error": "Invalid URL provided",
                    "content": ""
                }
            
            logger.info(f"Scraping URL: {url}")
            
            # Make request with timeout
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extract title
            title = soup.title.string.strip() if soup.title else "No title"
            
            # Extract main content
            # Try to find main content areas first
            content_selectors = [
                'main', 'article', '.content', '.main-content', 
                '#content', '#main', '.entry-content', '.post-content'
            ]
            
            content_text = ""
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content_text = content_elem.get_text(strip=True)
                    break
            
            # If no main content found, get all text
            if not content_text:
                content_text = soup.get_text(strip=True)
            
            # Clean and truncate content
            content_text = re.sub(r'\s+', ' ', content_text)  # Normalize whitespace
            if len(content_text) > max_chars:
                content_text = content_text[:max_chars] + "..."
            
            logger.info(f"Successfully scraped {len(content_text)} characters from {url}")
            
            return {
                "success": True,
                "url": url,
                "title": title,
                "content": content_text,
                "length": len(content_text)
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error scraping {url}: {e}")
            return {
                "success": False,
                "error": f"Failed to fetch URL: {str(e)}",
                "content": ""
            }
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {
                "success": False,
                "error": f"Scraping error: {str(e)}",
                "content": ""
            }
    
    def scrape_multiple_urls(self, urls: List[str], max_chars: int = 1500) -> List[Dict[str, Any]]:
        """Scrape multiple URLs and return results."""
        results = []
        for url in urls[:3]:  # Limit to 3 URLs to prevent overload
            result = self.scrape_url(url, max_chars)
            results.append(result)
        return results


class EnhancedChatTools:
    """Enhanced chat tools combining web search and scraping."""
    
    def __init__(self):
        self.search_tool = WebSearchTool()
        self.scraping_tool = WebScrapingTool()
    
    def search_and_scrape(self, query: str, scrape_results: bool = True) -> Dict[str, Any]:
        """Search the web and optionally scrape the top results."""
        # Perform search
        search_results = self.search_tool.search(query)
        
        response = {
            "query": query,
            "search_results": search_results,
            "scraped_content": []
        }
        
        if scrape_results and search_results:
            # Scrape top 2 results
            urls_to_scrape = [r["url"] for r in search_results[:2] if r.get("url") and r["url"] != "#"]
            if urls_to_scrape:
                scraped = self.scraping_tool.scrape_multiple_urls(urls_to_scrape)
                response["scraped_content"] = scraped
        
        return response
    
    def get_vinyl_comprehensive_info(self, artist: str, title: str) -> Dict[str, Any]:
        """Get comprehensive information about a vinyl record."""
        # Search for general info
        info_query = f"{artist} {title} vinyl record discography information history"
        info_results = self.search_tool.search(info_query, max_results=3)
        
        # Search for pricing info
        price_results = self.search_tool.search_vinyl_prices(artist, title)
        
        # Scrape top results for detailed content
        all_urls = []
        for result in (info_results + price_results)[:4]:
            if result.get("url") and result["url"] != "#":
                all_urls.append(result["url"])
        
        scraped_content = self.scraping_tool.scrape_multiple_urls(all_urls[:2])  # Limit scraping
        
        return {
            "artist": artist,
            "title": title,
            "general_info": info_results,
            "pricing_info": price_results,
            "detailed_content": scraped_content,
            "total_sources": len(info_results) + len(price_results)
        }
    
    def answer_vinyl_question(self, question: str, artist: str = "", title: str = "") -> Dict[str, Any]:
        """Answer a specific question about vinyl records using web search."""
        # Enhance query with context
        if artist and title:
            enhanced_query = f"{question} {artist} {title} vinyl record"
        else:
            enhanced_query = f"{question} vinyl record"
        
        return self.search_and_scrape(enhanced_query, scrape_results=True)