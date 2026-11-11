from __future__ import annotations

from typing import List

from agents.base_agent import BaseAgent
from tools.search_tools import search_flights
from utils.models import FlightOption, TripRequest


class FlightAgent(BaseAgent):
    name = "flight_agent"

    def run(self, request: TripRequest) -> List[FlightOption]:
        self.logger.info("Searching flights: %s -> %s", request.origin, request.destination)
        flights = search_flights(request.origin, request.destination, request.start_date)
        flights.sort(key=lambda f: f.price)
        return flights
