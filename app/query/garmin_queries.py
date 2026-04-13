"""Question-driven Garmin data fetch service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from app.garmin_auth import GarminClient

SUPPORTED_QUERY_TYPES = (
    "sleep_recovery",
    "training_state",
    "activity_history",
    "performance_prediction",
    "composite_health",
)


@dataclass
class GarminQueryService:
    """Fetch Garmin data domains for a supported question type."""

    auth_client: GarminClient

    @property
    def client(self) -> Any:
        return self.auth_client.client

    def run(
        self,
        question_type: str,
        *,
        target_date: date,
        days: int = 7,
    ) -> dict[str, Any]:
        if question_type not in SUPPORTED_QUERY_TYPES:
            raise ValueError(f"Unsupported question_type: {question_type}")

        if question_type == "sleep_recovery":
            return self.fetch_sleep_recovery(target_date)
        if question_type == "training_state":
            return self.fetch_training_state(target_date)
        if question_type == "activity_history":
            return self.fetch_activity_history(target_date, days=days)
        if question_type == "performance_prediction":
            return self.fetch_performance_prediction(target_date)
        return self.fetch_composite_health(target_date, days=days)

    def fetch_sleep_recovery(self, target_date: date) -> dict[str, Any]:
        target_date_str = target_date.isoformat()
        return {
            "sleep_today": self.client.get_sleep_data(target_date_str),
            "stress_today": self.client.get_stress_data(target_date_str),
            "respiration_today": self.client.get_respiration_data(target_date_str),
            "heart_rates_today": self.client.get_heart_rates(target_date_str),
        }

    def fetch_training_state(self, target_date: date) -> dict[str, Any]:
        target_date_str = target_date.isoformat()
        return {
            "training_readiness_today": self.client.get_training_readiness(target_date_str),
            "training_status_today": self.client.get_training_status(target_date_str),
            "sleep_today": self.client.get_sleep_data(target_date_str),
        }

    def fetch_activity_history(self, target_date: date, *, days: int) -> dict[str, Any]:
        window_days = max(days, 1)
        target_date_str = target_date.isoformat()
        activity_start = (target_date - timedelta(days=window_days)).isoformat()
        return {
            "activities_last_n_days": self.client.get_activities_by_date(activity_start, target_date_str),
            "window_days": window_days,
            "window_start": activity_start,
            "window_end": target_date_str,
        }

    def fetch_performance_prediction(self, target_date: date) -> dict[str, Any]:
        target_date_str = target_date.isoformat()
        return {
            "race_predictions_latest": self.client.get_race_predictions(),
            "training_status_today": self.client.get_training_status(target_date_str),
        }

    def fetch_composite_health(self, target_date: date, *, days: int) -> dict[str, Any]:
        window_days = max(days, 1)
        target_date_str = target_date.isoformat()
        activity_start = (target_date - timedelta(days=window_days)).isoformat()
        return {
            "sleep_today": self.client.get_sleep_data(target_date_str),
            "stress_today": self.client.get_stress_data(target_date_str),
            "heart_rates_today": self.client.get_heart_rates(target_date_str),
            "training_readiness_today": self.client.get_training_readiness(target_date_str),
            "training_status_today": self.client.get_training_status(target_date_str),
            "activities_last_n_days": self.client.get_activities_by_date(activity_start, target_date_str),
            "window_days": window_days,
            "window_start": activity_start,
            "window_end": target_date_str,
        }
