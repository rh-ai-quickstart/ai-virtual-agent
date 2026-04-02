import logging
import os
from typing import Any, Dict

import requests
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hotel_mcp")

mcp = FastMCP(
    "hotel_mcp",
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8000")),
)


@mcp.tool()
def google_hotels_search(
    destination: str,
    start_date: str,
    end_date: str,
    adults: int = 2,
    preferences: str = "",
) -> str:
    """Find hotel options for a destination and date range using SerpApi Google Hotels."""
    logger.info("google_hotels_search destination=%s", destination)
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return "SERPAPI_API_KEY is not set. Provide it to enable hotel research."
    if not destination:
        return "Destination is required to search hotels."

    query = destination
    if preferences:
        query = f"{destination} {preferences}"

    params: Dict[str, Any] = {
        "engine": "google_hotels",
        "q": query,
        "hl": "en",
        "gl": "us",
        "check_in_date": start_date,
        "check_out_date": end_date,
        "currency": "USD",
        "api_key": api_key,
    }
    if adults:
        params["adults"] = adults

    def _fetch(search_params: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.get(
            "https://serpapi.com/search.json",
            params=search_params,
            timeout=30,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"SerpApi error {response.status_code}: {response.text}")
        response.raise_for_status()
        return response.json()

    try:
        data = _fetch(params)
    except RuntimeError as exc:
        return str(exc)

    properties = data.get("properties") or data.get("hotels") or []
    if not properties:
        retry_params = dict(params)
        retry_params["q"] = f"{query} hotels"
        try:
            data = _fetch(retry_params)
        except RuntimeError as exc:
            return str(exc)
        properties = data.get("properties") or data.get("hotels") or []
        if not properties:
            return (
                "No hotels returned from SerpApi. "
                f"Tried query='{params['q']}' and '{retry_params['q']}'."
            )

    formatted = []
    for prop in properties[:6]:
        name = prop.get("name", "Unknown hotel")
        rate = prop.get("rate_per_night", {}).get("lowest", "")
        rating = prop.get("rating", "")
        location = prop.get("location", "")
        formatted.append(f"- {name} | {location} | rating: {rating} | rate: {rate}")

    return "\n".join(formatted)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
