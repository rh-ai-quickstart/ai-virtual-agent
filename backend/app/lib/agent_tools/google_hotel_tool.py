import os
from typing import Any, Dict, Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class GoogleHotelsInput(BaseModel):
    """Input schema for GoogleHotelsTool."""

    destination: str = Field(..., description="City or area for the hotel search.")
    start_date: str = Field(..., description="Check-in date (YYYY-MM-DD).")
    end_date: str = Field(..., description="Check-out date (YYYY-MM-DD).")
    adults: int = Field(2, description="Number of adults.")
    budget: str = Field("mid-range", description="Budget preference.")
    preferences: str = Field("", description="Amenities or location preferences.")


class GoogleHotelsTool(BaseTool):
    name: str = "google_hotels_search"
    description: str = (
        "Search for hotels using SerpApi's Google Hotels API. "
        "Requires SERPAPI_API_KEY env var."
    )
    args_schema: Type[BaseModel] = GoogleHotelsInput

    def _run(
        self,
        destination: str,
        start_date: str,
        end_date: str,
        adults: int = 2,
        budget: str = "mid-range",
        preferences: str = "",
    ) -> str:
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

        response = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        properties = data.get("properties") or data.get("hotels") or []
        if not properties:
            return "No hotels returned from SerpApi."

        formatted = []
        for prop in properties[:6]:
            name = prop.get("name", "Unknown hotel")
            rate = prop.get("rate_per_night", {}).get("lowest", "")
            rating = prop.get("rating", "")
            location = prop.get("location", "")
            formatted.append(
                f"- {name} | {location} | rating: {rating} | rate: {rate}"
            )

        return "\n".join(formatted)
