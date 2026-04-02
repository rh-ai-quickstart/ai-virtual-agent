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
        "Search for hotels in a destination city. "
        "Returns hotel options with name, location, rating, and nightly rate."
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
            return "Error: SERPAPI_API_KEY is not set."
        if not destination:
            return "Error: destination is required."

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
            return "No hotels found for this destination and dates."

        formatted = []
        for prop in properties[:6]:
            name = prop.get("name", "Unknown hotel")
            rate = prop.get("rate_per_night", {}).get("lowest", "N/A")
            rating = prop.get("rating", "N/A")
            location = prop.get("location", "")
            amenities = ", ".join(prop.get("amenities", [])[:3]) or ""
            line = f"**{name}**"
            if location:
                line += f" — {location}"
            line += f"\n  Rating: {rating} | Rate: {rate}/night"
            if amenities:
                line += f" | Amenities: {amenities}"
            formatted.append(line)

        return "\n\n".join(formatted)
