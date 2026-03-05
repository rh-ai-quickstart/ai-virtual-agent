import os
from typing import Any, Dict, Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


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
