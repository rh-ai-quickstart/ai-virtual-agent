import os
from typing import Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class TavilySearchInput(BaseModel):
    """Input schema for TavilySearchTool."""

    query: str = Field(..., description="Search query for travel research.")
    max_results: int = Field(5, description="Max results to return.")


class TavilySearchTool(BaseTool):
    name: str = "tavily_travel_search"
    description: str = (
        "Search the web for travel information using Tavily. "
        "Use for attractions, seasonal considerations, and local tips."
    )
    args_schema: Type[BaseModel] = TavilySearchInput

    def _run(self, query: str, max_results: int = 5) -> str:
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
