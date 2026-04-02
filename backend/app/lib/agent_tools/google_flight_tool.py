import os
from typing import Any, Dict, Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class GoogleFlightsInput(BaseModel):
    """Input schema for GoogleFlightsTool."""

    origin: str = Field(
        description="Origin city or airport code (e.g. 'New York' or 'JFK')."
    )
    destination: str = Field(
        description="Destination city or airport code (e.g. 'Cancun' or 'CUN')."
    )
    depart_date: str = Field(description="Departure date in YYYY-MM-DD format.")
    return_date: str = Field(
        "", description="Return date in YYYY-MM-DD format. Required for round-trip."
    )
    passengers: int = Field(1, description="Number of passengers.")
    cabin: str = Field(
        "economy", description="Cabin class: economy, business, or first."
    )


class GoogleFlightsTool(BaseTool):
    name: str = "google_flights_search"
    description: str = (
        "Search for round-trip flights between two cities. "
        "Returns flight options with airline, price, duration, and stops. "
        "Requires origin, destination, depart_date, and return_date."
    )
    args_schema: Type[BaseModel] = GoogleFlightsInput

    def _run(
        self,
        origin: str,
        destination: str,
        depart_date: str,
        return_date: str = "",
        passengers: int = 1,
        cabin: str = "economy",
    ) -> str:
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return "Error: SERPAPI_API_KEY is not set."
        if not origin or not destination:
            return "Error: origin and destination are required."
        if not return_date:
            return "Error: return_date is required for round-trip. Use YYYY-MM-DD."

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
            "type": 1,
            "return_date": return_date,
            "adults": passengers,
            "travel_class": travel_class,
            "hl": "en",
            "gl": "us",
            "api_key": api_key,
        }
        response = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=30,
        )
        if response.status_code >= 400:
            return (
                f"Error: SerpApi returned {response.status_code}: {response.text[:200]}"
            )
        data = response.json()
        flights = data.get("best_flights") or data.get("other_flights") or []
        if not flights:
            return "No flights found for this route and dates."

        formatted = []
        for option in flights[:5]:
            price = option.get("price", "N/A")
            duration = option.get("total_duration", "N/A")
            segments = option.get("flights", [])
            stops = max(len(segments) - 1, 0)
            if segments:
                first = segments[0]
                airline = first.get("airline", "Unknown")
                flight_num = first.get("flight_number", "")
                dep = first.get("departure_airport", {}).get("id", origin)
                arr = segments[-1].get("arrival_airport", {}).get("id", destination)
            else:
                airline, flight_num, dep, arr = "Unknown", "", origin, destination
            stop_text = "nonstop" if stops == 0 else f"{stops} stop(s)"
            formatted.append(
                f"**{airline} {flight_num}** {dep} → {arr} | "
                f"{duration} min | {stop_text} | ${price}"
            )

        return "\n".join(formatted)
