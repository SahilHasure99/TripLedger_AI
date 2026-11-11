from agents.coordinator_agent import CoordinatorAgent
from utils.models import TripRequest


def test_coordinator_produces_full_trip_plan():
    request = TripRequest(
        destination="Tokyo",
        origin="New York",
        start_date="2026-11-01",
        end_date="2026-11-07",
        preferences=["food", "museums"],
    )
    plan = CoordinatorAgent().run(request)

    assert plan.request == request
    assert len(plan.flights) > 0
    assert len(plan.hotels) > 0
    assert len(plan.weather) > 0
    assert len(plan.itinerary) > 0
    assert "Trip Plan" in plan.summary()
