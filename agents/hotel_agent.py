from __future__ import annotations

from typing import List

from agents.base_agent import BaseAgent
from tools.search_tools import search_hotels
from utils.models import HotelOption, TripRequest


class HotelAgent(BaseAgent):
    name = "hotel_agent"

    def run(self, request: TripRequest) -> List[HotelOption]:
        self.logger.info("Searching hotels in %s", request.destination)
        hotels = search_hotels(request.destination)
        style = (getattr(request, "accommodation", "Any") or "Any").lower()
        if style == "luxury":
            hotels.sort(key=lambda h: (h.rating, h.price_per_night), reverse=True)
        elif style == "comfort":
            # Prefer highly rated options without automatically choosing the most expensive.
            hotels.sort(key=lambda h: (float(h.rating) / max(float(h.price_per_night), 1), h.rating), reverse=True)
        else:
            # Budget and Any both lead with the lowest indicative nightly price.
            hotels.sort(key=lambda h: h.price_per_night)
        return hotels
