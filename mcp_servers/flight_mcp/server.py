import json
import logging
import os
import re
from typing import Any, Dict, Iterable

import requests
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flight_mcp")

mcp = FastMCP(
    "flight_mcp",
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8000")),
)


def _extract_iata(value: str) -> str:
    match = re.search(r"\b([A-Z]{3})\b", value.upper())
    return match.group(1) if match else ""


def _coerce_list(value: str) -> list[str]:
    raw = value.strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass
    json_match = re.search(r"\[[\s\S]*?\]", raw)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
    if "\n" in raw:
        lines = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]
        cleaned = [line for line in lines if "http" not in line.lower()]
        cleaned = [
            line
            for line in cleaned
            if "json array" not in line.lower()
            and "here is" not in line.lower()
            and not line.startswith("```")
        ]
        return cleaned if cleaned else lines
    return [item.strip() for item in raw.split(",") if item.strip()]


def _extract_city_candidates(items: list[str]) -> list[str]:
    candidates: list[str] = []
    for item in items:
        if not item:
            continue
        if "," in item:
            parts = [part.strip() for part in item.split(",") if part.strip()]
            if parts:
                candidates.append(parts[-1])
            continue
        candidates.append(item)
    return candidates


def _extract_first_location(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list) and parsed:
            return str(parsed[0])
    except json.JSONDecodeError:
        pass
    if "\n" in raw:
        lines = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]
        cleaned = [line for line in lines if "http" not in line.lower()]
        return cleaned[0] if cleaned else lines[0]
    return raw


_CITY_AIRPORT_MAP: Dict[str, str] = {
    "paris": "CDG",
    "london": "LHR",
    "new york": "JFK",
    "los angeles": "LAX",
    "chicago": "ORD",
    "san francisco": "SFO",
    "tokyo": "NRT",
    "rome": "FCO",
    "berlin": "BER",
    "madrid": "MAD",
    "amsterdam": "AMS",
    "dubai": "DXB",
    "singapore": "SIN",
    "hong kong": "HKG",
    "sydney": "SYD",
    "toronto": "YYZ",
    "mumbai": "BOM",
    "bangkok": "BKK",
    "istanbul": "IST",
    "seoul": "ICN",
    "miami": "MIA",
    "washington": "IAD",
    "boston": "BOS",
    "atlanta": "ATL",
    "dallas": "DFW",
    "denver": "DEN",
    "seattle": "SEA",
    "lisbon": "LIS",
    "barcelona": "BCN",
    "mexico city": "MEX",
}


def _find_iata_in_candidates(candidates: Iterable[dict]) -> str:
    for item in candidates:
        if not isinstance(item, dict):
            continue
        for key in ("iata_code", "iata", "code"):
            code = item.get(key)
            if isinstance(code, str) and _extract_iata(code):
                return _extract_iata(code)
    return ""


def _resolve_airport_code(value: str, api_key: str) -> str:
    value = _extract_first_location(value)

    known = _CITY_AIRPORT_MAP.get(value.lower().strip())
    if known:
        return known

    code = _extract_iata(value)
    if code:
        return code

    for query in (value, f"{value} airport", f"{value} international airport"):
        try:
            response = requests.get(
                "https://serpapi.com/locations.json",
                params={"q": query, "api_key": api_key},
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.warning("IATA lookup failed for %s: %s", query, exc)
            continue

        if isinstance(data, list):
            code = _find_iata_in_candidates(data)
            if code:
                return code
        elif isinstance(data, dict):
            for key in ("locations", "suggested_locations", "airports"):
                if isinstance(data.get(key), list):
                    code = _find_iata_in_candidates(data.get(key))
                    if code:
                        return code
    return ""


@mcp.tool()
def iata_lookup(location: str) -> str:
    """Resolve a city/region into a 3-letter IATA airport code."""
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return "SERPAPI_API_KEY is not set. Provide it to enable flight research."
    if not location:
        return "Location is required to resolve IATA code."

    code = _resolve_airport_code(location, api_key)
    if not code:
        return "Unable to resolve IATA code for location."
    return code


@mcp.tool()
def google_flights_search(
    origin: str,
    destination: str,
    depart_date: str,
    return_date: str,
    passengers: int = 1,
    cabin: str = "economy",
) -> str:
    """Find round-trip flight options using SerpApi Google Flights."""
    logger.info("google_flights_search origin=%s destination=%s", origin, destination)
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return "SERPAPI_API_KEY is not set. Provide it to enable flight research."
    if not origin or not destination:
        return "Origin and destination are required to search flights."
    if not return_date:
        return "return_date is required for round-trip searches. Provide YYYY-MM-DD."

    origin_code = _resolve_airport_code(origin, api_key)
    if not origin_code:
        return (
            "Unable to resolve origin airport code. Provide a 3-letter IATA code "
            "(e.g., RDU, SFO)."
        )

    cabin_map = {
        "economy": 1,
        "premium_economy": 2,
        "business": 3,
        "first": 4,
    }
    travel_class = cabin_map.get(cabin.lower(), 1)

    destinations = _coerce_list(destination) or [destination]
    city_candidates = _extract_city_candidates(destinations)
    if city_candidates:
        destinations = city_candidates
    selected = []
    if destinations:
        selected.append(destinations[0])
    if len(destinations) > 1:
        selected.append(destinations[-1])
    max_destinations = 2
    results = []

    for dest in selected[:max_destinations]:
        destination_code = _resolve_airport_code(dest, api_key)
        if not destination_code:
            continue

        params: Dict[str, Any] = {
            "engine": "google_flights",
            "departure_id": origin_code,
            "arrival_id": destination_code,
            "outbound_date": depart_date,
            "return_date": return_date,
            "type": 1,
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
            results.append(
                f"- SerpApi error {response.status_code} for "
                f"{destination_code}: {response.text}"
            )
            continue
        response.raise_for_status()
        data = response.json()
        flights = data.get("best_flights") or data.get("other_flights") or []
        if not flights:
            results.append(f"- No flights returned for {destination_code}.")
            continue

        results.append(f"Destination {destination_code}:")
        for option in flights[:5]:
            price = option.get("price")
            duration = option.get("total_duration")
            segments = option.get("flights", [])
            if segments:
                first = segments[0]
                airline = first.get("airline", "Unknown airline")
                flight_num = first.get("flight_number", "")
                dep = first.get("departure_airport", {}).get("id", origin_code)
                arr = first.get("arrival_airport", {}).get("id", destination_code)
            else:
                airline = "Unknown airline"
                flight_num = ""
                dep = origin_code
                arr = destination_code
            results.append(
                f"- {airline} {flight_num} {dep}->{arr} "
                f"| {duration} mins | ${price}"
            )

    return "\n".join(results)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
