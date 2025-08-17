"""Wikipedia search tool service."""
import logging
import aiohttp
from typing import List, Dict, Any, Optional

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
                "origin": "*"
            }

            async with session.get(self.base_url, params=search_params) as response:
                search_data = await response.json()

            search_results = search_data.get("query", {}).get("search", [])

            if not search_results:
                logger.info(
                    "wikipedia.search.no_results",
                    extra={"search_id": search_id, "query": query}
                )
                return []

            # Get page extracts for found articles
            page_titles = [result["title"] for result in search_results]
            extract_params = {
                "action": "query",
                "prop": "extracts|info",
                "exintro": "true",
                "explaintext": "true",
                "exsectionformat": "plain",
                "titles": "|".join(page_titles),
                "inprop": "url",
                "format": "json",
                "origin": "*"
            }

            async with session.get(self.base_url, params=extract_params) as response:
                extract_data = await response.json()

            pages = extract_data.get("query", {}).get("pages", {})

            results = []
            for page_id, page_data in pages.items():
                if page_id != "-1":  # Valid page
                    results.append({
                        "title": page_data.get("title", ""),
                        "extract": page_data.get("extract", "")[:500],  # Limit extract length
                        "url": page_data.get("fullurl", ""),
                        "page_id": page_id
                    })

            logger.info(
                "wikipedia.search.success",
                extra={
                    "search_id": search_id,
                    "query": query,
                    "results_count": len(results)
                }
            )

            return results[:limit]  # Ensure we don't exceed the limit

        except Exception as e:
            logger.error(
                "wikipedia.search.error",
                extra={
                    "search_id": search_id,
                    "query": query,
                    "error": str(e)
                }
            )
            return []

    def get_tool_definition(self) -> Dict[str, Any]:
        """Return tool definition for LLM function calling."""
        return {
            "type": "function",
            "function": {
                "name": "wikipedia_search",
                "description": "Search Wikipedia for information about a topic",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for Wikipedia"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 3)",
                            "default": 3,
                            "minimum": 1,
                            "maximum": 5
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()


# Global instance
wikipedia_tool = WikipediaSearchTool()
