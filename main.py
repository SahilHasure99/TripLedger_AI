"""CLI entry point for the multi-agent traveller system."""
from __future__ import annotations

import argparse

from agents.coordinator_agent import CoordinatorAgent
from utils.models import TripRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-Agent Traveller")
    parser.add_argument("--origin", default="New York")
    parser.add_argument("--destination", required=True)
    parser.add_argument("--start-date", dest="start_date", required=True)
    parser.add_argument("--end-date", dest="end_date", required=True)
    parser.add_argument("--budget", type=float, default=None)
    parser.add_argument("--travelers", type=int, default=1)
    parser.add_argument(
        "--preferences",
        nargs="*",
        default=[],
        help="e.g. --preferences museums food nightlife",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    request = TripRequest(
        destination=args.destination,
        origin=args.origin,
        start_date=args.start_date,
        end_date=args.end_date,
        budget=args.budget,
        travelers=args.travelers,
        preferences=args.preferences,
    )

    coordinator = CoordinatorAgent()
    plan = coordinator.run(request)

    print("\n" + "=" * 50)
    print(plan.summary())
    print("=" * 50)

    print("\nFlights:")
    for f in plan.flights:
        print(f"  - {f.airline}: ${f.price:.2f} ({f.duration_hours}h)")

    print("\nHotels:")
    for h in plan.hotels:
        print(f"  - {h.name} ({h.neighborhood}): ${h.price_per_night:.2f}/night, {h.rating}*")

    print("\nWeather:")
    for w in plan.weather:
        print(f"  - {w.date}: {w.summary}, {w.low_c}-{w.high_c}C")

    print("\nItinerary:")
    for day in plan.itinerary:
        print(f"  Day {day.day_number} ({day.date}):")
        for activity in day.activities:
            print(f"    * {activity}")


if __name__ == "__main__":
    main()
