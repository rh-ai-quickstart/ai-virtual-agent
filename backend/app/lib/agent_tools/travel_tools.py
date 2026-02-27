import os
from typing import Any, Dict, Type

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


class GoogleFlightsInput(BaseModel):
    """Input schema for GoogleFlightsTool."""

    origin: str = Field(..., description="Origin city or airport code.")
    destination: str = Field(..., description="Destination city or airport code.")
    depart_date: str = Field(..., description="Departure date (YYYY-MM-DD).")
    return_date: str = Field("", description="Return date (YYYY-MM-DD).")
    passengers: int = Field(1, description="Number of passengers.")
    cabin: str = Field("economy", description="Cabin class preference.")


class GoogleFlightsTool(BaseTool):
    name: str = "google_flights_search"
    description: str = (
        "Search for flights using SerpApi's Google Flights API. "
        "Requires SERPAPI_API_KEY env var."
    )
    args_schema: Type[BaseModel] = GoogleFlightsInput

    def _run(
        self,
        origin: str,
        destination: str,
        depart_date: str,
        return_date: str,
        passengers: int = 1,
        cabin: str = "economy",
    ) -> str:
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return "SERPAPI_API_KEY is not set. Provide it to enable flight research."
        if not origin or not destination:
            return "Origin and destination are required to search flights."
        if not return_date:
            return "return_date is required for round-trip searches. Provide YYYY-MM-DD."

        cabin_map = {
            "economy": 1,
            "premium_economy": 2,
            "business": 3,
            "first": 4,
        }
        travel_class = cabin_map.get(cabin.lower(), 1)

        params: Dict[str, Any] = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": depart_date,
            "adults": passengers,
            "travel_class": travel_class,
            "hl": "en",
            "gl": "us",
            "api_key": api_key,
        }
        if return_date:
            params["type"] = 1
            params["return_date"] = return_date
        else:
            params["type"] = 2
        response = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=30,
        )
        if response.status_code >= 400:
            return f"SerpApi error {response.status_code}: {response.text}"
        response.raise_for_status()
        data = response.json()
        flights = data.get("best_flights") or data.get("other_flights") or []
        if not flights:
            return "No flights returned from SerpApi."

        formatted = []
        for option in flights[:5]:
            price = option.get("price")
            duration = option.get("total_duration")
            segments = option.get("flights", [])
            if segments:
                first = segments[0]
                airline = first.get("airline", "Unknown airline")
                flight_num = first.get("flight_number", "")
                dep = first.get("departure_airport", {}).get("id", origin)
                arr = first.get("arrival_airport", {}).get("id", destination)
            else:
                airline = "Unknown airline"
                flight_num = ""
                dep = origin
                arr = destination
            formatted.append(
                f"- {airline} {flight_num} {dep}->{arr} | "
                f"{duration} mins | ${price}"
            )

        return "\n".join(formatted)
