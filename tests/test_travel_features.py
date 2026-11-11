from datetime import date
from types import SimpleNamespace

import pytest

from utils.travel_features import (
    google_maps_search_url,
    google_hotel_photos_url,
    google_location_search_url,
    search_destination_catalog,
    trip_fingerprint,
    validate_trip,
    trip_to_text,
    budget_breakdown,
)
from agents.itinerary_agent import ItineraryAgent
from utils.models import TripRequest, WeatherForecast


def test_hotel_links_are_google_searches_and_encode_spaces():
    maps = google_maps_search_url("The Green House", "Pune, India")
    photos = google_hotel_photos_url("The Green House", "Pune, India")
    assert maps.startswith("https://www.google.com/maps/search/?api=1&query=")
    assert "The+Green+House" in maps
    assert photos.startswith("https://www.google.com/search?q=")
    with pytest.raises(ValueError):
        google_maps_search_url("  ", "Pune")


def test_fingerprint_is_stable_and_changes_with_inputs():
    a = trip_fingerprint("Pune", "Goa", "2026-11-01", "2026-11-04", 10000, 2, ["Nature", "Food"])
    b = trip_fingerprint(" pune ", "GOA", "2026-11-01", "2026-11-04", 10000, 2, ["Food", "Nature"])
    c = trip_fingerprint("Pune", "Goa", "2026-11-01", "2026-11-04", 10000, 3, ["Nature", "Food"])
    assert a == b
    assert a != c


def test_validation_covers_empty_invalid_dates_and_budget():
    errors = validate_trip(" ", "", date(2026, 11, 5), date(2026, 11, 5), 0, 0)
    assert len(errors) == 5
    assert validate_trip("Pune", "Goa", date(2026, 11, 1), date(2026, 11, 3), 5000, 2) == []


def test_itinerary_matches_exact_requested_duration_and_pace():
    req = TripRequest("Goa", "Pune", "2026-11-01", "2026-11-03", 10000, 2, ["Nature"], pace="Packed")
    weather = [WeatherForecast("2026-11-01", "Sunny", 31, 24)]
    days = ItineraryAgent().run(req, weather)
    assert len(days) == 2
    assert days[0].date == "2026-11-01"
    assert len([a for a in days[1].activities if not a.startswith("Preference-based")]) == 3


def test_itinerary_handles_single_day_trip_and_missing_weather():
    req = TripRequest("Goa", "Pune", "2026-11-01", "2026-11-02", 10000, 1)
    days = ItineraryAgent().run(req, [])
    assert len(days) == 1
    assert days[0].date == "2026-11-01"


def test_budget_breakdown_and_text_export_are_safe():
    request = SimpleNamespace(origin="Pune", destination="Goa", start_date="2026-11-01", end_date="2026-11-03", travelers=2, budget=20000)
    plan = SimpleNamespace(request=request, flights=[SimpleNamespace(airline="Example Air", departure="08:00", arrival="09:00", duration_hours=1, price=2000)], hotels=[SimpleNamespace(name="Green Hotel", neighborhood="Central", rating=4.2, price_per_night=1500)], weather=[], itinerary=[])
    budget = budget_breakdown(plan)
    assert budget["Flights (estimate)"] == 4000
    assert budget["Accommodation (estimate)"] == 3000
    assert budget["Total budget"] == 20000
    text = trip_to_text(plan)
    assert "Pune → Goa" in text
    assert "Green Hotel" in text
    assert "must be verified" in text


def test_pdf_and_docx_exports_generate_valid_file_signatures():
    from utils.travel_features import trip_to_pdf, trip_to_docx
    request = SimpleNamespace(origin="Pune", destination="Goa", start_date="2026-11-01", end_date="2026-11-03", travelers=2, budget=20000)
    plan = SimpleNamespace(request=request, flights=[], hotels=[], weather=[], itinerary=[])
    pdf_bytes = trip_to_pdf(plan)
    docx_bytes = trip_to_docx(plan)
    assert pdf_bytes.startswith(b"%PDF-")
    assert docx_bytes.startswith(b"PK\x03\x04")
    assert len(pdf_bytes) > 500
    assert len(docx_bytes) > 500


def test_duplicate_submit_cache_calls_factory_only_once_and_is_bounded():
    from utils.travel_features import get_or_create_cached_plan
    cache = {}
    calls = []
    factory = lambda: calls.append("generated") or {"trip": "goa"}
    first, reused_first = get_or_create_cached_plan(cache, "same-trip", factory, max_entries=2)
    second, reused_second = get_or_create_cached_plan(cache, "same-trip", factory, max_entries=2)
    assert first == second == {"trip": "goa"}
    assert reused_first is False
    assert reused_second is True
    assert len(calls) == 1
    get_or_create_cached_plan(cache, "trip-2", factory, max_entries=2)
    get_or_create_cached_plan(cache, "trip-3", factory, max_entries=2)
    assert len(cache) == 2


def test_original_travelmate_ui_contract_remains_present():
    from pathlib import Path
    source = Path(__file__).resolve().parents[1] / "app.py"
    app_text = source.read_text(encoding="utf-8")
    assert 'page_title="TravelMate | Explore Beyond"' in app_text
    assert 'Recommended Hotels' in app_text
    assert 'Day-by-Day Itinerary' in app_text
    assert 'google_maps_search_url' in app_text
    assert 'fadeUp' in app_text


def test_location_search_url_encodes_arbitrary_places_and_rejects_empty():
    url = google_location_search_url("Shibuya Crossing, Tokyo")
    assert url.startswith("https://www.google.com/maps/search/?api=1&query=")
    assert "Shibuya+Crossing%2C+Tokyo" in url
    with pytest.raises(ValueError):
        google_location_search_url("   ")


def test_destination_catalog_search_is_case_insensitive_bounded_and_empty_safe():
    catalogue = {"cities": {"places": [
        {"name": "Goa, India", "description": "Beach escape", "highlights": ["Seafood"]},
        {"name": "Kyoto, Japan", "description": "Historic temples", "highlights": ["Culture"]},
        {"name": "Bali, Indonesia", "description": "Island escape", "highlights": ["Surfing"]},
    ]}}
    assert search_destination_catalog(catalogue, "gOa")[0]["name"] == "Goa, India"
    assert search_destination_catalog(catalogue, "temples")[0]["name"] == "Kyoto, Japan"
    assert search_destination_catalog(catalogue, "missing") == []
    assert search_destination_catalog(catalogue, " ") == []
    assert len(search_destination_catalog(catalogue, "escape", limit=1)) == 1


def test_search_ui_keeps_original_brand_and_includes_animated_character_and_custom_location_flow():
    from pathlib import Path
    source = Path(__file__).resolve().parents[1] / "app.py"
    app_text = source.read_text(encoding="utf-8")
    assert 'page_title="TravelMate | Explore Beyond"' in app_text
    assert 'class="tm-search-panel"' in app_text
    assert 'class="tm-search-character"' in app_text
    assert 'key="location_search_input"' in app_text
    assert 'View destination on Google Maps' in app_text
    assert 'custom_destination' in app_text
