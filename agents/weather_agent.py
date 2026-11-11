from __future__ import annotations

from typing import List

from agents.base_agent import BaseAgent
from tools.search_tools import get_weather_forecast
from utils.models import TripRequest, WeatherForecast


class WeatherAgent(BaseAgent):
    name = "weather_agent"

    def run(self, request: TripRequest) -> List[WeatherForecast]:
        self.logger.info("Fetching weather for %s", request.destination)
        return get_weather_forecast(request.destination, request.start_date, request.end_date)
