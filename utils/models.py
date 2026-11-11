"""Shared data models passed between agents."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TripRequest:
    destination: str
    origin: str = "Unknown"
    start_date: str = ""
    end_date: str = ""
    budget: Optional[float] = None
    travelers: int = 1
    preferences: List[str] = field(default_factory=list)
    pace: str = "Balanced"
    accommodation: str = "Any"


@dataclass
class FlightOption:
    airline: str
    departure: str
    arrival: str
    price: float
    duration_hours: float


@dataclass
class HotelOption:
    name: str
    neighborhood: str
    price_per_night: float
    rating: float


@dataclass
class WeatherForecast:
    date: str
    summary: str
    high_c: float
    low_c: float


@dataclass
class ItineraryDay:
    day_number: int
    date: str
    activities: List[str]


@dataclass
class TripPlan:
    request: TripRequest
    flights: List[FlightOption] = field(default_factory=list)
    hotels: List[HotelOption] = field(default_factory=list)
    weather: List[WeatherForecast] = field(default_factory=list)
    itinerary: List[ItineraryDay] = field(default_factory=list)

    def summary(self) -> str:
        lines = [f"Trip Plan: {self.request.origin} -> {self.request.destination}"]
        lines.append(f"Dates: {self.request.start_date} to {self.request.end_date}")
        if self.flights:
            best = min(self.flights, key=lambda f: f.price)
            lines.append(f"Best flight: {best.airline} (${best.price:.0f})")
        if self.hotels:
            best_hotel = min(self.hotels, key=lambda h: h.price_per_night)
            lines.append(
                f"Best hotel: {best_hotel.name} (${best_hotel.price_per_night:.0f}/night)"
            )
        if self.itinerary:
            lines.append(f"Itinerary: {len(self.itinerary)} day(s) planned")
        return "\n".join(lines)
