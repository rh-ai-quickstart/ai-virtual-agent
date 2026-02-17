import logging
import os

import requests
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("travel_research_mcp")

mcp = FastMCP(
    "travel_research_mcp",
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8000")),
)


@mcp.tool()
def tavily_travel_search(query: str, max_results: int = 5) -> str:
    """Search the web for travel information about a destination or theme."""
    logger.info("tavily_travel_search query=%s", query)
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "TAVILY_API_KEY is not set. Provide it to enable web research."

    response = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": True,
            "include_raw_content": False,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    results = data.get("results", [])
    if not results:
        return "No results returned from Tavily."

    formatted = []
    for item in results:
        title = item.get("title", "Untitled")
        url = item.get("url", "")
        snippet = item.get("content", "")
        formatted.append(f"- {title} ({url}): {snippet}")
    return "\n".join(formatted)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
