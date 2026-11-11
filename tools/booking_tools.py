"""Stub booking helpers.

Wire these up to real booking APIs (or leave as confirmation-only stubs)
once you're ready to let agents actually reserve flights/hotels.
"""
from __future__ import annotations

from utils.logger import get_logger

logger = get_logger(__name__)


def book_flight(flight_option) -> str:
    logger.info("Booking flight with %s for $%.2f", flight_option.airline, flight_option.price)
    return f"CONFIRMED-FLIGHT-{hash(flight_option.airline) % 10000}"


def book_hotel(hotel_option) -> str:
    logger.info("Booking hotel: %s ($%.2f/night)", hotel_option.name, hotel_option.price_per_night)
    return f"CONFIRMED-HOTEL-{hash(hotel_option.name) % 10000}"
