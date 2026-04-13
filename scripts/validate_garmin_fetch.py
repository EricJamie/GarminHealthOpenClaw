#!/usr/bin/env python3
"""Run a live Garmin data fetch validation against the current account."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.garmin_auth import GarminClient
from app.garmin_auth.config import GarminAuthConfig


def _dig(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except Exception:  # noqa: BLE001
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
        if current is None:
            return None
    return current


def _top_keys(value: Any) -> list[str]:
    if isinstance(value, dict):
        return list(value.keys())[:20]
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return list(value[0].keys())[:20]
    return []


def _has_nested_key(value: Any, target: str) -> bool:
    target = target.lower()
    if isinstance(value, dict):
        for key, nested in value.items():
            if target in str(key).lower():
                return True
            if _has_nested_key(nested, target):
                return True
    elif isinstance(value, list):
        for item in value[:20]:
            if _has_nested_key(item, target):
                return True
    return False


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate live Garmin data fetches")
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="How many days of activities to inspect for the activity validation",
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Target date in YYYY-MM-DD for daily wellness endpoints",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    parser.add_argument(
        "--show-values",
        action="store_true",
        help="Include preview_values with representative field values",
    )
    return parser


def _preview_fields(name: str, value: Any) -> dict[str, Any]:
    preview_map = {
        "user_profile": [
            "id",
            "userData.genderType",
            "userData.height",
            "userData.weight",
            "userSleep.sleepTime",
        ],
        "personal_record": [
            "0.prTypeLabelKey",
            "0.value",
            "0.activityName",
            "0.activityStartDateTimeLocal",
        ],
        "sleep_today": [
            "dailySleepDTO.calendarDate",
            "dailySleepDTO.sleepTimeSeconds",
            "dailySleepDTO.deepSleepSeconds",
            "dailySleepDTO.lightSleepSeconds",
            "dailySleepDTO.remSleepSeconds",
            "dailySleepDTO.avgSleepStress",
            "dailySleepDTO.avgHeartRate",
            "dailySleepDTO.sleepScores.overall.value",
            "avgOvernightHrv",
            "hrvStatus.status",
            "bodyBatteryChange",
        ],
        "stress_today": [
            "calendarDate",
            "maxStressLevel",
            "avgStressLevel",
            "bodyBatteryValuesArray.0",
            "stressValuesArray.0",
        ],
        "respiration_today": [
            "calendarDate",
            "lowestRespirationValue",
            "highestRespirationValue",
            "avgWakingRespirationValue",
            "avgSleepRespirationValue",
        ],
        "heart_rates_today": [
            "calendarDate",
            "maxHeartRate",
            "minHeartRate",
            "restingHeartRate",
            "lastSevenDaysAvgRestingHeartRate",
        ],
        "training_readiness_today": [
            "0.level",
            "0.score",
            "0.sleepScore",
            "0.recoveryTime",
            "0.acuteLoad",
            "0.hrvWeeklyAverage",
        ],
        "training_status_today": [
            "mostRecentVO2Max.generic.calendarDate",
            "mostRecentVO2Max.generic.vo2MaxValue",
            "mostRecentVO2Max.generic.vo2MaxPreciseValue",
            "mostRecentTrainingLoadBalance.metricsTrainingLoadBalanceDTOMap.3609281851.trainingBalanceFeedbackPhrase",
            "mostRecentTrainingStatus.latestTrainingStatusData.3609281851.trainingStatus",
        ],
        "steps_today": [
            "0.startGMT",
            "0.steps",
            "0.primaryActivityLevel",
            "1.steps",
        ],
        "floors_today": [
            "startTimestampLocal",
            "floorValuesArray.0",
            "floorsValueDescriptorDTOList.0.key",
        ],
        "intensity_minutes_today": [
            "calendarDate",
            "weeklyModerate",
            "weeklyVigorous",
            "weeklyTotal",
            "moderateMinutes",
            "vigorousMinutes",
        ],
        "race_predictions_latest": [
            "calendarDate",
            "time5K",
            "time10K",
            "timeHalfMarathon",
            "timeMarathon",
        ],
        "activities_last_n_days": [
            "0.activityName",
            "0.activityType.typeKey",
            "0.startTimeLocal",
            "0.distance",
            "0.duration",
            "0.averageHR",
            "0.calories",
        ],
    }

    result: dict[str, Any] = {}
    for path in preview_map.get(name, []):
        result[path] = _dig(value, path)
    return result


def main() -> None:
    args = _build_parser().parse_args()

    config = GarminAuthConfig.from_env()
    if not config.token_data:
        raise SystemExit("GARMIN_TOKEN_DATA is not set in the environment or .env")

    target_date = date.fromisoformat(args.date)
    activity_start = (target_date - timedelta(days=max(args.days, 1))).isoformat()
    target_date_str = target_date.isoformat()

    client = GarminClient(
        token_data=config.token_data,
        email="",
        password="",
    )

    checks = [
        ("user_profile", lambda: client.client.get_user_profile()),
        ("personal_record", lambda: client.client.get_personal_record()),
        ("sleep_today", lambda: client.client.get_sleep_data(target_date_str)),
        ("stress_today", lambda: client.client.get_stress_data(target_date_str)),
        ("respiration_today", lambda: client.client.get_respiration_data(target_date_str)),
        ("heart_rates_today", lambda: client.client.get_heart_rates(target_date_str)),
        ("training_readiness_today", lambda: client.client.get_training_readiness(target_date_str)),
        ("training_status_today", lambda: client.client.get_training_status(target_date_str)),
        ("steps_today", lambda: client.client.get_steps_data(target_date_str)),
        ("floors_today", lambda: client.client.get_floors(target_date_str)),
        ("intensity_minutes_today", lambda: client.client.get_intensity_minutes_data(target_date_str)),
        ("race_predictions_latest", lambda: client.client.get_race_predictions()),
        ("activities_last_n_days", lambda: client.client.get_activities_by_date(activity_start, target_date_str)),
    ]

    results: dict[str, Any] = {}
    for name, fn in checks:
        try:
            value = fn()
            entry = {
                "ok": True,
                "type": type(value).__name__,
                "size": len(value) if hasattr(value, "__len__") else None,
                "top_keys": _top_keys(value),
            }
            for probe in ["hrv", "bodyBattery", "vo2", "load", "stress", "sleep", "prediction"]:
                entry[f"has_{probe}"] = _has_nested_key(value, probe)
            if args.show_values:
                entry["preview_values"] = _preview_fields(name, value)
            results[name] = entry
        except Exception as exc:  # noqa: BLE001
            results[name] = {
                "ok": False,
                "error": type(exc).__name__,
                "message": str(exc)[:300],
            }

    sample_activities: list[dict[str, Any]] = []
    activity_result = results.get("activities_last_n_days", {})
    if activity_result.get("ok"):
        activities = client.client.get_activities_by_date(activity_start, target_date_str)
        for activity in activities[:3]:
            if isinstance(activity, dict):
                sample_activities.append(
                    {
                        "activityId": activity.get("activityId"),
                        "activityName": activity.get("activityName"),
                        "activityType": activity.get("activityType", {}),
                        "startTimeLocal": activity.get("startTimeLocal"),
                        "distance": activity.get("distance"),
                        "duration": activity.get("duration"),
                    }
                )

    output = {
        "collected_for_date": target_date_str,
        "display_name": getattr(client.client, "display_name", None),
        "full_name": getattr(client.client, "full_name", None),
        "results": results,
        "sample_activities": sample_activities,
    }
    indent = 2 if args.pretty else None
    print(json.dumps(output, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main()
