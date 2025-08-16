"""Wikipedia search tool service."""
import logging
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


class WikipediaSearchTool:
    """Wikipedia search tool for retrieving relevant articles."""

    def __init__(self):
        self.base_url = "https://en.wikipedia.org/w/api.php"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def search(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Search Wikipedia for articles matching the query.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of dictionaries containing article information
        """
        search_id = f"wiki_search_{hash(query) % 10000}"
        logger.info(
            "wikipedia.search.request",
            extra={
                "search_id": search_id,
                "query": query,
                "limit": limit
            }
        )

        try:
            session = await self._get_session()

            # First, search for page titles
            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": limit,
                "format": "json",
                "srprop": "snippet|titlesnippet|size|wordcount"
            }

            async with session.get(self.base_url, params=search_params) as response:
                if response.status != 200:
                    logger.error(
                        "wikipedia.search.error",
                        extra={
                            "search_id": search_id,
                            "status": response.status,
                            "error": "HTTP error from Wikipedia API"
                        }
                    )
                    return []

                search_data = await response.json()
                search_results = search_data.get("query", {}).get("search", [])

                if not search_results:
                    logger.info(
                        "wikipedia.search.no_results",
                        extra={"search_id": search_id, "query": query}
                    )
                    return []

                # Get page IDs for content extraction
                page_ids = [str(result["pageid"]) for result in search_results]

                # Get page content/extracts
                content_params = {
                    "action": "query",
                    "prop": "extracts|info",
                    "pageids": "|".join(page_ids),
                    "exintro": "true",
                    "explaintext": "true",
                    "exsectionformat": "plain",
                    "exchars": "500",
                    "inprop": "url",
                    "format": "json"
                }

                async with session.get(self.base_url, params=content_params) as content_response:
                    if content_response.status != 200:
                        logger.error(
                            "wikipedia.content.error",
                            extra={
                                "search_id": search_id,
                                "status": content_response.status,
                                "error": "HTTP error from Wikipedia API for content"
                            }
                        )
                        return []

                    content_data = await content_response.json()
                    pages = content_data.get("query", {}).get("pages", {})

                    # Combine search results with content
                    results = []
                    for search_result in search_results:
                        page_id = str(search_result["pageid"])
                        page_data = pages.get(page_id, {})

                        result = {
                            "title": search_result["title"],
                            "snippet": search_result.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", ""),
                            "extract": page_data.get("extract", ""),
                            "url": page_data.get("fullurl", f"https://en.wikipedia.org/wiki/{quote(search_result['title'])}"),
                            "wordcount": search_result.get("wordcount", 0),
                            "size": search_result.get("size", 0)
                        }
                        results.append(result)

                    logger.info(
                        "wikipedia.search.success",
                        extra={
                            "search_id": search_id,
                            "query": query,
                            "results_count": len(results)
                        }
                    )

                    return results

        except asyncio.TimeoutError:
            logger.error(
                "wikipedia.search.timeout",
                extra={"search_id": search_id, "query": query}
            )
            return []
        except Exception as exc:
            logger.error(
                "wikipedia.search.exception",
                extra={
                    "search_id": search_id,
                    "query": query,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc)
                },
                exc_info=True
            )
            return []

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    def get_tool_definition(self) -> Dict[str, Any]:
        """Get the tool definition for Cohere's tool calling."""
        return {
            "type": "function",
            "function": {
                "name": "wikipedia_search",
                "description": "Search Wikipedia for information on a given topic. Returns relevant article excerpts and links.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to look up on Wikipedia"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 3)",
                            "minimum": 1,
                            "maximum": 5,
                            "default": 3
                        }
                    },
                    "required": ["query"]
                }
            }
        }


# Global instance
wikipedia_tool = WikipediaSearchTool()
