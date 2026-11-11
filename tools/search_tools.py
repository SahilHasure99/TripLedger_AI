"""Data-fetching helpers used by agents.

Weather uses the free Open-Meteo API (no key required).
Flight and hotel data use realistic estimates based on distance and
destination metadata — ready for future integration with Amadeus /
Skyscanner (flights) or Booking.com / Expedia (hotels).
"""
from __future__ import annotations

import math
import random
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import requests

from utils.models import FlightOption, HotelOption, WeatherForecast

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# Geocoding  (Open-Meteo free geocoding — no API key)
# ─────────────────────────────────────────────────────────

# Some destination names in the app don't geocode well (e.g. "Swiss Alps").
# This lookup provides accurate fallback coordinates.
_KNOWN_COORDINATES: dict[str, Tuple[float, float]] = {
    "swiss alps":       (46.69, 7.87),      # Interlaken area
    "bali":             (-8.4095, 115.1889),
    "maldives":         (3.2028, 73.2207),
    "phuket":           (7.8804, 98.3923),
    "manali":           (32.2396, 77.1887),
    "patagonia":        (-50.3418, -72.2646),
    "santorini":        (36.3932, 25.4615),
    "goa":              (15.2993, 74.124),
    "amalfi coast":     (40.6340, 14.6027),
    "kolhapur":         (16.6954, 74.2315),
    "pune":             (18.5204, 73.8567),
    "mumbai":           (19.0760, 72.8777),
    "delhi":            (28.7041, 77.1025),
    "new delhi":        (28.6139, 77.2090),
    "bangalore":        (12.9716, 77.5946),
    "chennai":          (13.0827, 80.2707),
    "hyderabad":        (17.3850, 78.4867),
    "london":           (51.5074, -0.1278),
    "paris":            (48.8566, 2.3522),
    "new york":         (40.7128, -74.0060),
    "tokyo":            (35.6762, 139.6503),
    "dubai":            (25.2048, 55.2708),
    "singapore":        (1.3521, 103.8198),
    "switzerland":      (46.8182, 8.2275),
    "japan":            (35.6762, 139.6503),
    "thailand":         (13.7563, 100.5018),
    "new zealand":      (-40.9006, 174.8860),
    "iceland":          (64.1466, -21.9426),
    "dolomites":        (46.4333, 11.8500),
    "sikkim":           (27.5330, 88.5122),
    "banff":            (51.1784, -115.5708),
    "swiss jura":       (47.2500, 7.1500),
    "gulmarg":          (34.0484, 74.3805),
    "zermatt":          (45.9765, 7.7491),
    "queenstown":       (-45.0312, 168.6626),
    "leh-ladakh":       (34.1526, 77.5771),
    "leh":              (34.1526, 77.5771),
    "chamonix":         (45.9237, 6.8694),
    "langkawi":         (6.3500, 99.8000),
    "krabi":            (8.0863, 98.9063),
    "mauritius":        (-20.3484, 57.5522),
    "zanzibar":         (-6.1659, 39.2026),
    "algarve":          (37.0194, -7.9304),
    "pondicherry":      (11.9416, 79.8083),
    "palawan":          (9.8349, 118.7384),
    "kovalam":          (8.4004, 76.9787),
}


def _geocode(place_name: str) -> Optional[Tuple[float, float]]:
    """Return (latitude, longitude) for *place_name*.

    Checks a local lookup first, then falls back to Open-Meteo Geocoding API.
    """
    key = place_name.strip().lower()

    # Check local known coordinates
    for known_key, coords in _KNOWN_COORDINATES.items():
        if known_key in key or key in known_key:
            return coords

    # Fallback: Open-Meteo geocoding API
    try:
        resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": place_name, "count": 1, "format": "json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results")
        if results:
            return (results[0]["latitude"], results[0]["longitude"])
    except Exception as exc:
        logger.warning("Geocoding failed for '%s': %s", place_name, exc)

    return None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ─────────────────────────────────────────────────────────
# Flights — realistic estimates based on distance
# ─────────────────────────────────────────────────────────

# Airline pools per route region
_INDIAN_DOMESTIC_AIRLINES = ["IndiGo", "Air India", "SpiceJet", "Vistara", "Akasa Air"]
_INTERNATIONAL_AIRLINES = ["Air India", "Emirates", "Lufthansa", "Singapore Airlines", "Qatar Airways", "Swiss International"]
_SHORT_HAUL_AIRLINES = ["IndiGo", "Air India Express", "Thai AirAsia", "SpiceJet"]

_AVG_SPEED_KMH = 850  # average commercial jet speed


def search_flights(origin: str, destination: str, date: str) -> List[FlightOption]:
    """Generate realistic flight options based on actual distance."""

    origin_coords = _geocode(origin)
    dest_coords = _geocode(destination)

    if not origin_coords or not dest_coords:
        logger.warning(
            "Could not geocode origin/destination (%s / %s). Using fallback data.",
            origin, destination,
        )
        return _fallback_flights(origin, destination, date)

    distance_km = _haversine_km(*origin_coords, *dest_coords)

    # Pick airline pool based on distance
    if distance_km < 1500:
        airline_pool = _INDIAN_DOMESTIC_AIRLINES
    elif distance_km < 5000:
        airline_pool = _SHORT_HAUL_AIRLINES + ["Air India", "Emirates"]
    else:
        airline_pool = _INTERNATIONAL_AIRLINES

    # Select 3 distinct airlines
    airlines = random.sample(airline_pool, min(3, len(airline_pool)))

    flights: List[FlightOption] = []
    for airline in airlines:
        # Base flight time from distance + add layover time for long routes
        base_hours = distance_km / _AVG_SPEED_KMH

        # Add realistic overhead: taxiing, ascent, descent (~0.5-1h)
        flight_hours = base_hours + random.uniform(0.5, 1.0)

        # Longer routes might have a layover (adds 1.5-3h)
        is_direct = True
        if distance_km > 4000 and random.random() < 0.5:
            flight_hours += random.uniform(1.5, 3.0)
            is_direct = False
        elif distance_km > 7000 and random.random() < 0.7:
            flight_hours += random.uniform(2.0, 4.0)
            is_direct = False

        flight_hours = round(flight_hours, 1)

        # Pricing based on distance (₹3-6 per km, varies by airline)
        base_price_per_km = random.uniform(3.0, 6.5)
        price_inr = distance_km * base_price_per_km

        # Budget airlines are 20-35% cheaper
        if airline in ("IndiGo", "SpiceJet", "Air India Express", "Thai AirAsia", "Akasa Air"):
            price_inr *= random.uniform(0.65, 0.80)

        # Premium airlines have a surcharge
        if airline in ("Emirates", "Singapore Airlines", "Swiss International", "Lufthansa"):
            price_inr *= random.uniform(1.15, 1.40)

        price_inr = round(price_inr, 2)

        # Calculate arrival time from departure
        try:
            dep_dt = datetime.fromisoformat(f"{date}T08:00:00")
        except (ValueError, TypeError):
            dep_dt = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

        # Vary departure times per airline
        dep_offset_hours = random.choice([0, 1, 2, 4, 6, 10])
        dep_dt = dep_dt + timedelta(hours=dep_offset_hours)
        arr_dt = dep_dt + timedelta(hours=flight_hours)

        route_type = "Direct" if is_direct else "1 Stop"

        flights.append(
            FlightOption(
                airline=airline,
                departure=f"{origin} {dep_dt.strftime('%Y-%m-%d %H:%M')}",
                arrival=f"{destination} {arr_dt.strftime('%Y-%m-%d %H:%M')}",
                price=price_inr,
                duration_hours=flight_hours,
            )
        )

    flights.sort(key=lambda f: f.price)
    return flights


def _fallback_flights(origin: str, destination: str, date: str) -> List[FlightOption]:
    """Simple fallback when geocoding fails."""
    airlines = ["Air India", "IndiGo", "Emirates"]
    return [
        FlightOption(
            airline=airline,
            departure=f"{origin} {date} 08:00",
            arrival=f"{destination} {date} 14:00",
            price=round(random.uniform(15000, 60000), 2),
            duration_hours=round(random.uniform(3, 12), 1),
        )
        for airline in airlines
    ]


# ─────────────────────────────────────────────────────────
# Hotels — destination-aware realistic data
# ─────────────────────────────────────────────────────────

# Real neighborhoods and hotel styles per destination
_DESTINATION_HOTELS: dict[str, list[dict]] = {
    "swiss alps": [
        {"name": "Hotel Interlaken", "neighborhood": "Interlaken Ost", "base_price": 12000},
        {"name": "Victoria-Jungfrau Grand Hotel", "neighborhood": "Höheweg", "base_price": 35000},
        {"name": "Alpine Lodge", "neighborhood": "Grindelwald", "base_price": 8500},
    ],
    "bali": [
        {"name": "The Mulia Bali", "neighborhood": "Nusa Dua", "base_price": 15000},
        {"name": "Komaneka at Bisma", "neighborhood": "Ubud", "base_price": 8000},
        {"name": "W Bali - Seminyak", "neighborhood": "Seminyak", "base_price": 12000},
    ],
    "maldives": [
        {"name": "Soneva Fushi", "neighborhood": "Baa Atoll", "base_price": 60000},
        {"name": "Coco Palm Dhuni Kolhu", "neighborhood": "Dhuni Kolhu", "base_price": 35000},
        {"name": "Adaaran Prestige Vadoo", "neighborhood": "South Malé Atoll", "base_price": 25000},
    ],
    "phuket": [
        {"name": "The Nai Harn", "neighborhood": "Nai Harn Beach", "base_price": 7000},
        {"name": "Kata Rocks", "neighborhood": "Kata", "base_price": 14000},
        {"name": "Pullman Phuket Panwa Beach", "neighborhood": "Panwa", "base_price": 5500},
    ],
    "manali": [
        {"name": "The Himalayan", "neighborhood": "Log Huts Area", "base_price": 6000},
        {"name": "Johnson Lodge & Spa", "neighborhood": "Circuit House Rd", "base_price": 4500},
        {"name": "Solang Valley Resort", "neighborhood": "Solang Valley", "base_price": 3500},
    ],
    "patagonia": [
        {"name": "The Singular Patagonia", "neighborhood": "Puerto Natales", "base_price": 22000},
        {"name": "Tierra Patagonia", "neighborhood": "Torres del Paine", "base_price": 30000},
        {"name": "Hotel Lago Grey", "neighborhood": "Grey Glacier", "base_price": 18000},
    ],
    "santorini": [
        {"name": "Canaves Oia Suites", "neighborhood": "Oia", "base_price": 25000},
        {"name": "Santo Maris Oia", "neighborhood": "Oia", "base_price": 20000},
        {"name": "Aressana Spa Hotel", "neighborhood": "Fira", "base_price": 8000},
    ],
    "goa": [
        {"name": "Taj Fort Aguada", "neighborhood": "Sinquerim", "base_price": 8000},
        {"name": "Alila Diwa Goa", "neighborhood": "Majorda", "base_price": 6500},
        {"name": "The Leela Goa", "neighborhood": "Cavelossim", "base_price": 10000},
    ],
    "amalfi coast": [
        {"name": "Hotel Santa Caterina", "neighborhood": "Amalfi", "base_price": 28000},
        {"name": "Le Sirenuse", "neighborhood": "Positano", "base_price": 45000},
        {"name": "Hotel Caruso", "neighborhood": "Ravello", "base_price": 38000},
    ],
}


def search_hotels(destination: str) -> List[HotelOption]:
    """Return realistic hotel options for the destination."""
    key = destination.strip().lower()

    # Find matching destination in our database
    matched_hotels = None
    for dest_key, hotels in _DESTINATION_HOTELS.items():
        if dest_key in key or key in dest_key:
            matched_hotels = hotels
            break

    if not matched_hotels:
        # Generic fallback with reasonable data
        matched_hotels = [
            {"name": f"{destination} Grand Hotel", "neighborhood": "City Center", "base_price": 8000},
            {"name": f"{destination} Boutique Stay", "neighborhood": "Old Quarter", "base_price": 5000},
            {"name": f"The {destination} Resort", "neighborhood": "Suburb", "base_price": 12000},
        ]

    results: List[HotelOption] = []
    for hotel in matched_hotels:
        # Add ±20% variation to base price for realism
        price = hotel["base_price"] * random.uniform(0.80, 1.20)
        rating = round(random.uniform(4.0, 4.9), 1)
        results.append(
            HotelOption(
                name=hotel["name"],
                neighborhood=hotel["neighborhood"],
                price_per_night=round(price, 2),
                rating=rating,
            )
        )

    results.sort(key=lambda h: h.price_per_night)
    return results


# ─────────────────────────────────────────────────────────
# Weather — Real data from Open-Meteo API (free, no key)
# ─────────────────────────────────────────────────────────

# WMO weather codes → human-readable descriptions
_WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Freezing drizzle",
    57: "Heavy freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def get_weather_forecast(
    destination: str, start_date: str, end_date: str
) -> List[WeatherForecast]:
    """Fetch real weather forecast from Open-Meteo API."""

    coords = _geocode(destination)
    if not coords:
        logger.warning("Could not geocode '%s' for weather. Using fallback.", destination)
        return _fallback_weather(start_date, end_date)

    lat, lon = coords

    # Determine exact number of trip nights/days requested
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        trip_days = max(1, (end_dt - start_dt).days)
        # Open-Meteo forecast is limited to ~16 days from today
        max_end = datetime.now() + timedelta(days=15)
        if end_dt > max_end:
            end_dt = max_end
        if start_dt > max_end:
            # Date is too far in the future for a forecast — use historical averages approach
            return _fallback_weather_for_location(lat, lon, start_date, end_date)
    except (ValueError, TypeError):
        trip_days = None

    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,weathercode",
                "timezone": "auto",
                "start_date": start_date,
                "end_date": end_date,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        highs = daily.get("temperature_2m_max", [])
        lows = daily.get("temperature_2m_min", [])
        codes = daily.get("weathercode", [])

        forecasts: List[WeatherForecast] = []
        limit = min(len(dates), trip_days) if trip_days is not None else len(dates)
        for i in range(limit):
            summary = _WMO_CODES.get(codes[i], "Unknown") if i < len(codes) else "Unknown"
            forecasts.append(
                WeatherForecast(
                    date=f"Day {i + 1}",
                    summary=summary,
                    high_c=round(highs[i], 1) if i < len(highs) else 0,
                    low_c=round(lows[i], 1) if i < len(lows) else 0,
                )
            )
        return forecasts if forecasts else _fallback_weather(start_date, end_date)

    except Exception as exc:
        logger.warning("Open-Meteo API call failed: %s. Using fallback.", exc)
        return _fallback_weather_for_location(lat, lon, start_date, end_date)


def _fallback_weather_for_location(
    lat: float, lon: float, start_date: str, end_date: str
) -> List[WeatherForecast]:
    """Estimate weather from latitude and month when forecast API can't cover the dates."""
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        num_days = max((end_dt - start_dt).days, 1)
    except (ValueError, TypeError):
        num_days = 3
        start_dt = datetime.now()

    # Rough temperature estimate based on latitude and month
    month = start_dt.month
    abs_lat = abs(lat)

    # Base temperature from latitude (tropical vs temperate vs polar)
    if abs_lat < 15:
        base_high = 32  # tropical
        base_low = 23
    elif abs_lat < 30:
        base_high = 28
        base_low = 18
    elif abs_lat < 45:
        base_high = 20
        base_low = 10
    elif abs_lat < 60:
        base_high = 12
        base_low = 3
    else:
        base_high = 5
        base_low = -5

    # Seasonal adjustment (Northern Hemisphere winter = colder)
    is_northern = lat >= 0
    winter_months = [12, 1, 2] if is_northern else [6, 7, 8]
    summer_months = [6, 7, 8] if is_northern else [12, 1, 2]

    if month in winter_months:
        base_high -= 8
        base_low -= 8
    elif month in summer_months:
        base_high += 5
        base_low += 3

    summaries = ["Partly cloudy", "Clear sky", "Slight rain", "Overcast", "Mainly clear"]

    forecasts: List[WeatherForecast] = []
    for i in range(num_days):
        high = round(base_high + random.uniform(-3, 3), 1)
        low = round(base_low + random.uniform(-3, 3), 1)
        forecasts.append(
            WeatherForecast(
                date=f"Day {i + 1}",
                summary=random.choice(summaries),
                high_c=high,
                low_c=low,
            )
        )
    return forecasts


def _fallback_weather(start_date: str, end_date: str) -> List[WeatherForecast]:
    """Last-resort fallback when nothing else works."""
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        num_days = max((end_dt - start_dt).days, 1)
    except (ValueError, TypeError):
        num_days = 3

    summaries = ["Partly cloudy", "Clear sky", "Slight rain", "Overcast"]
    return [
        WeatherForecast(
            date=f"Day {i + 1}",
            summary=random.choice(summaries),
            high_c=round(random.uniform(15, 30), 1),
            low_c=round(random.uniform(5, 18), 1),
        )
        for i in range(num_days)
    ]
