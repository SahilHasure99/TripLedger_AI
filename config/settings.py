"""Centralized application configuration.

Loads values from environment variables (and a local .env file, if present)
so agents and tools never hardcode secrets or config values.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    model_name: str = os.getenv("MODEL_NAME", "gemini-1.5-flash")

    flight_api_key: str = os.getenv("FLIGHT_API_KEY", "")
    hotel_api_key: str = os.getenv("HOTEL_API_KEY", "")
    weather_api_key: str = os.getenv("WEATHER_API_KEY", "")

    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
