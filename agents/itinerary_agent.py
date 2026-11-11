from __future__ import annotations

import json
from datetime import date, timedelta
from typing import List

from agents.base_agent import BaseAgent
from config.settings import settings
from utils.models import ItineraryDay, TripRequest, WeatherForecast

_ACTIVITY_BANK = [
    "Explore the historic old town",
    "Visit the main art museum",
    "Try local street food at the night market",
    "Take a guided walking tour",
    "Relax at a nearby park or waterfront",
    "Visit a popular viewpoint or landmark",
    "Shop at the local markets",
]


class ItineraryAgent(BaseAgent):
    """Builds a rich day-by-day itinerary.

    If GEMINI_API_KEY is configured in settings or environment, leverages
    Google Gemini to produce intelligent, destination-customized, and
    weather-aware daily recommendations. Otherwise, cleanly falls back
    to the deterministic planner with zero downtime.
    """

    name = "itinerary_agent"

    def run(self, request: TripRequest, weather: List[WeatherForecast]) -> List[ItineraryDay]:
        self.logger.info("Building itinerary for %s", request.destination)
        try:
            start = date.fromisoformat(request.start_date)
            end = date.fromisoformat(request.end_date)
            num_days = max(1, (end - start).days)
        except (TypeError, ValueError):
            num_days = max(1, len(weather))
            start = None

        pace = (getattr(request, "pace", "Balanced") or "Balanced").lower()
        activity_count = 1 if pace == "relaxed" else 3 if pace == "packed" else 2

        # ─── Live AI generation if key is provided ───
        if settings.gemini_api_key and settings.gemini_api_key.strip() not in {"", "your_gemini_api_key_here"}:
            try:
                import google.generativeai as genai

                genai.configure(api_key=settings.gemini_api_key.strip())
                model = genai.GenerativeModel(settings.model_name or "gemini-1.5-flash")

                weather_summary = ", ".join([f"{w.date}: {w.summary} ({w.high_c}°C)" for w in weather[:num_days]])
                prompt = (
                    f"You are TripLedger AI's elite travel concierge. Generate a structured {num_days}-day itinerary for "
                    f"a trip to {request.destination} departing from {request.origin}. "
                    f"Travel pace: {pace}. Travelers: {request.travelers}. "
                    f"Preferences: {', '.join(request.preferences) if request.preferences else 'General sights, culture & cuisine'}. "
                    f"Forecast: {weather_summary}.\n\n"
                    f"Respond ONLY with valid JSON in this exact structure without markdown backticks:\n"
                    f"[\n"
                    f'  {{"day_number": 1, "activities": ["Activity 1", "Activity 2"]}},\n'
                    f"  ...\n"
                    f"]\n"
                    f"Provide exactly {num_days} days, with {activity_count} to {activity_count + 1} realistic, engaging activities per day."
                )

                response = model.generate_content(prompt)
                raw_text = response.text.strip()
                if raw_text.startswith("```"):
                    lines = raw_text.splitlines()
                    raw_text = "\n".join([line for line in lines if not line.startswith("```")])
                
                ai_data = json.loads(raw_text)
                if isinstance(ai_data, list) and len(ai_data) == num_days:
                    days = []
                    for i, d in enumerate(ai_data):
                        day_date = weather[i].date if i < len(weather) else (start + timedelta(days=i)).isoformat() if start else f"Day {i + 1}"
                        acts = d.get("activities", [])
                        if not acts:
                            acts = ["Explore downtown & local culture"]
                        days.append(
                            ItineraryDay(
                                day_number=i + 1,
                                date=day_date,
                                activities=acts,
                            )
                        )
                    self.logger.info("Successfully synthesized itinerary with Gemini AI.")
                    return days
            except Exception as exc:
                self.logger.warning("Gemini AI generation failed (%s). Falling back gracefully.", exc)

        # ─── Deterministic Fallback Planner ───
        days = []
        for i in range(num_days):
            start_idx = (i * activity_count) % len(_ACTIVITY_BANK)
            activities = [_ACTIVITY_BANK[(start_idx + j) % len(_ACTIVITY_BANK)] for j in range(activity_count)]
            if request.preferences:
                activities.append(f"Preference-based activity: {request.preferences[0]}")
            day_date = weather[i].date if i < len(weather) else (start + timedelta(days=i)).isoformat() if start else f"Day {i + 1}"
            days.append(
                ItineraryDay(
                    day_number=i + 1,
                    date=day_date,
                    activities=activities,
                )
            )
        return days
