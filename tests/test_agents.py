from agents.flight_agent import FlightAgent
from agents.hotel_agent import HotelAgent
from agents.itinerary_agent import ItineraryAgent
from agents.weather_agent import WeatherAgent
from utils.models import TripRequest


def make_request() -> TripRequest:
    return TripRequest(
        destination="Tokyo",
        origin="New York",
        start_date="2026-11-01",
        end_date="2026-11-07",
        preferences=["food"],
    )


def test_flight_agent_returns_sorted_flights():
    flights = FlightAgent().run(make_request())
    assert len(flights) > 0
    prices = [f.price for f in flights]
    assert prices == sorted(prices)


def test_hotel_agent_returns_sorted_hotels():
    hotels = HotelAgent().run(make_request())
    assert len(hotels) > 0
    prices = [h.price_per_night for h in hotels]
    assert prices == sorted(prices)


def test_weather_agent_returns_forecasts_for_requested_trip_duration():
    request = make_request()
    weather = WeatherAgent().run(request)
    # One forecast per trip day; API fallback may return estimated data offline.
    assert len(weather) == 6
    assert all(item.summary for item in weather)


def test_itinerary_agent_builds_days_matching_weather():
    request = make_request()
    weather = WeatherAgent().run(request)
    itinerary = ItineraryAgent().run(request, weather)
    assert len(itinerary) == len(weather)
    assert all(day.activities for day in itinerary)
