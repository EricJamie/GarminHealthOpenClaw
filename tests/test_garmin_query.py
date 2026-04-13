"""Minimal tests for question-driven Garmin query helpers."""

from __future__ import annotations

import unittest
from datetime import date

from app.context.query_result import build_query_result
from app.query.garmin_queries import GarminQueryService
from scripts.garmin_query import _build_parser


class _FakeUnderlyingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def get_sleep_data(self, value: str) -> dict[str, object]:
        self.calls.append(("get_sleep_data", (value,)))
        return {
            "dailySleepDTO": {
                "calendarDate": value,
                "sleepTimeSeconds": 18000,
                "sleepScores": {"overall": {"value": 71}},
            },
            "avgOvernightHrv": 65,
            "bodyBatteryChange": 40,
        }

    def get_stress_data(self, value: str) -> dict[str, object]:
        self.calls.append(("get_stress_data", (value,)))
        return {"calendarDate": value, "avgStressLevel": 28, "maxStressLevel": 70}

    def get_respiration_data(self, value: str) -> dict[str, object]:
        self.calls.append(("get_respiration_data", (value,)))
        return {"calendarDate": value, "avgSleepRespirationValue": 12}

    def get_heart_rates(self, value: str) -> dict[str, object]:
        self.calls.append(("get_heart_rates", (value,)))
        return {"calendarDate": value, "restingHeartRate": 46}

    def get_training_readiness(self, value: str) -> list[dict[str, object]]:
        self.calls.append(("get_training_readiness", (value,)))
        return [{"calendarDate": value, "level": "GOOD", "score": 74, "sleepScore": 71}]

    def get_training_status(self, value: str) -> dict[str, object]:
        self.calls.append(("get_training_status", (value,)))
        return {
            "mostRecentVO2Max": {"generic": {"calendarDate": value, "vo2MaxValue": 58.0}},
            "mostRecentTrainingLoadBalance": {
                "metricsTrainingLoadBalanceDTOMap": {"1": {"trainingBalanceFeedbackPhrase": "BALANCED"}}
            },
            "mostRecentTrainingStatus": {"latestTrainingStatusData": {"1": {"trainingStatus": 2}}},
        }

    def get_activities_by_date(self, start: str, end: str) -> list[dict[str, object]]:
        self.calls.append(("get_activities_by_date", (start, end)))
        return [
            {
                "activityId": 1,
                "activityName": "Morning Run",
                "activityType": {"typeKey": "running"},
                "startTimeLocal": f"{end} 07:00:00",
                "distance": 10000.0,
                "duration": 3200.0,
                "averageHR": 140.0,
                "calories": 700.0,
            }
        ]

    def get_race_predictions(self) -> dict[str, object]:
        self.calls.append(("get_race_predictions", ()))
        return {
            "calendarDate": "2026-04-13",
            "time5K": 1200,
            "time10K": 2500,
            "timeHalfMarathon": 5600,
            "timeMarathon": 12800,
        }


class _FakeAuthClient:
    def __init__(self) -> None:
        self.client = _FakeUnderlyingClient()


class GarminQueryTests(unittest.TestCase):
    def test_parser_supports_three_query_types(self) -> None:
        parser = _build_parser()
        parsed = parser.parse_args(["sleep_recovery"])
        self.assertEqual(parsed.question_type, "sleep_recovery")

    def test_sleep_recovery_fetches_expected_domains(self) -> None:
        service = GarminQueryService(_FakeAuthClient())
        result = service.run("sleep_recovery", target_date=date(2026, 4, 13))

        self.assertIn("sleep_today", result)
        self.assertIn("stress_today", result)
        self.assertIn("respiration_today", result)
        self.assertIn("heart_rates_today", result)

    def test_training_state_query_result_has_expected_shape(self) -> None:
        service = GarminQueryService(_FakeAuthClient())
        raw = service.run("training_state", target_date=date(2026, 4, 13))
        result = build_query_result(
            "training_state",
            raw,
            target_date=date(2026, 4, 13),
            display_name="runner",
            full_name="Runner",
        )

        self.assertEqual(result["question_type"], "training_state")
        self.assertIn("meta", result)
        self.assertIn("data", result)
        self.assertIn("highlights", result)
        self.assertIn("missing", result)
        self.assertIn("guidance", result)
        self.assertEqual(result["data"]["training_state"]["training_readiness"]["score"], 74)
        self.assertEqual(result["highlights"]["vo2max_value"], 58.0)
        self.assertEqual(result["highlights"]["training_readiness_band"], "high")
        self.assertIn("recommendation", result["guidance"])

    def test_activity_history_includes_window_and_items(self) -> None:
        service = GarminQueryService(_FakeAuthClient())
        raw = service.run("activity_history", target_date=date(2026, 4, 13), days=7)
        result = build_query_result(
            "activity_history",
            raw,
            target_date=date(2026, 4, 13),
            display_name="runner",
            full_name="Runner",
        )

        self.assertEqual(result["meta"]["source_window"]["window_days"], 7)
        self.assertEqual(result["data"]["recent_activities"]["count"], 1)
        self.assertEqual(result["data"]["recent_activities"]["items"][0]["activity_type"], "running")
        self.assertEqual(result["highlights"]["latest_activity_distance_km"], 10.0)
        self.assertTrue(result["highlights"]["activity_structure"]["mostly_endurance"])

    def test_performance_prediction_includes_prediction_and_vo2max(self) -> None:
        service = GarminQueryService(_FakeAuthClient())
        raw = service.run("performance_prediction", target_date=date(2026, 4, 13))
        result = build_query_result(
            "performance_prediction",
            raw,
            target_date=date(2026, 4, 13),
            display_name="runner",
            full_name="Runner",
        )

        self.assertEqual(result["highlights"]["time_half_marathon_seconds"], 5600)
        self.assertEqual(result["highlights"]["vo2max_value"], 58.0)
        self.assertEqual(result["highlights"]["time_5k_minutes"], 20.0)

    def test_composite_health_includes_summary_across_domains(self) -> None:
        service = GarminQueryService(_FakeAuthClient())
        raw = service.run("composite_health", target_date=date(2026, 4, 13), days=7)
        result = build_query_result(
            "composite_health",
            raw,
            target_date=date(2026, 4, 13),
            display_name="runner",
            full_name="Runner",
        )

        self.assertEqual(result["highlights"]["activity_count"], 1)
        self.assertEqual(result["highlights"]["avg_stress_level"], 28)
        self.assertEqual(result["data"]["composite_health"]["training_readiness"]["score"], 74)
        self.assertEqual(result["highlights"]["recent_activity_summary"]["latest_activity_distance_km"], 10.0)
        self.assertIn("rationale", result["guidance"])
        self.assertTrue(result["highlights"]["activity_structure"]["mostly_endurance"])


if __name__ == "__main__":
    unittest.main()
