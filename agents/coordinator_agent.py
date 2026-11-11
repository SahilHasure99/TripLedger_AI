"""Coordinator agent: orchestrates all specialized agents into a TripPlan."""
from __future__ import annotations

from agents.base_agent import BaseAgent
from agents.flight_agent import FlightAgent
from agents.hotel_agent import HotelAgent
from agents.itinerary_agent import ItineraryAgent
from agents.weather_agent import WeatherAgent
from utils.models import TripPlan, TripRequest


class CoordinatorAgent(BaseAgent):
    name = "coordinator_agent"

    def __init__(self) -> None:
        super().__init__()
        self.flight_agent = FlightAgent()
        self.hotel_agent = HotelAgent()
        self.weather_agent = WeatherAgent()
        self.itinerary_agent = ItineraryAgent()

    def run(self, request: TripRequest) -> TripPlan:
        self.logger.info("Coordinating trip plan for request: %s", request)

        flights = self.flight_agent.run(request)
        hotels = self.hotel_agent.run(request)
        weather = self.weather_agent.run(request)
        itinerary = self.itinerary_agent.run(request, weather)

        plan = TripPlan(
            request=request,
            flights=flights,
            hotels=hotels,
            weather=weather,
            itinerary=itinerary,
        )
        self.logger.info("Trip plan assembled successfully")
        return plan
