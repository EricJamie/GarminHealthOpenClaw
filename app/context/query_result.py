"""Normalize Garmin fetch results into a stable query-result shape."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional


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


def _collect_missing(value: dict[str, Any], required: dict[str, list[str]]) -> list[str]:
    missing: list[str] = []
    for domain, fields in required.items():
        domain_value = value.get(domain)
        if domain_value is None:
            missing.append(domain)
            continue
        for field in fields:
            if _dig(domain_value, field) is None:
                missing.append(f"{domain}.{field}")
    return missing


def _iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _round_or_none(value: Any, digits: int = 1) -> Any:
    if isinstance(value, (int, float)):
        return round(value, digits)
    return None


def _seconds_to_hours(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return round(value / 3600, 1)
    return None


def _minutes_to_hours(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return round(value / 60, 1)
    return None


def _seconds_to_minutes(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return round(value / 60, 1)
    return None


def _readiness_guidance_band(score: Any) -> Optional[str]:
    if not isinstance(score, (int, float)):
        return None
    if score <= 10:
        return "very_low"
    if score <= 40:
        return "low"
    if score <= 70:
        return "moderate"
    return "high"


def _latest_activity_summary(activities: list[dict[str, Any]]) -> dict[str, Any]:
    if not activities:
        return {}
    activity = activities[0]
    return {
        "latest_activity_name": activity.get("activity_name"),
        "latest_activity_type": activity.get("activity_type"),
        "latest_activity_distance_km": _round_or_none(
            (activity.get("distance_meters") or 0) / 1000 if activity.get("distance_meters") is not None else None
        ),
        "latest_activity_duration_hours": _seconds_to_hours(activity.get("duration_seconds")),
        "latest_activity_average_heart_rate": activity.get("average_heart_rate"),
    }


def _activity_type_counts(activities: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for activity in activities:
        activity_type = activity.get("activity_type")
        if not activity_type:
            continue
        counts[activity_type] = counts.get(activity_type, 0) + 1
    return counts


def _activity_structure_summary(activities: list[dict[str, Any]]) -> dict[str, Any]:
    counts = _activity_type_counts(activities)
    endurance_types = {"running", "road_biking", "cycling", "trail_running", "treadmill_running"}
    strength_types = {"strength_training", "strength", "cardio_strength", "functional_strength_training"}
    core_types = {"pilates", "yoga"}

    endurance_count = sum(count for kind, count in counts.items() if kind in endurance_types)
    strength_count = sum(count for kind, count in counts.items() if kind in strength_types)
    core_count = sum(count for kind, count in counts.items() if kind in core_types)

    dominant_types = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:3]
    return {
        "counts_by_type": counts,
        "endurance_count": endurance_count,
        "strength_count": strength_count,
        "core_mobility_count": core_count,
        "dominant_types": [{"activity_type": kind, "count": count} for kind, count in dominant_types],
        "mostly_endurance": endurance_count >= max(len(activities) - 1, 1) if activities else False,
        "has_recorded_strength": strength_count > 0,
        "has_recorded_core_mobility": core_count > 0,
    }


def _format_km(meters: Any) -> Any:
    if isinstance(meters, (int, float)):
        return round(meters / 1000, 1)
    return None


def _format_duration_hours(duration_seconds: Any) -> Any:
    return _seconds_to_hours(duration_seconds)


def _training_state_guidance(
    readiness_score: Any,
    recovery_time_minutes: Any,
    sleep_score: Any,
    vo2max_value: Any,
    load_balance_feedback: Any,
) -> dict[str, Any]:
    band = _readiness_guidance_band(readiness_score)
    recovery_hours = _minutes_to_hours(recovery_time_minutes)
    status = "neutral"
    summary = "今天状态中性，可以按感觉安排训练。"
    recommendation = "可以做常规训练，但注意根据体感控制强度。"

    if band == "very_low" or (isinstance(recovery_hours, (int, float)) and recovery_hours >= 36):
        status = "hold_back"
        summary = "今天更适合减量或恢复，不建议安排质量训练。"
        recommendation = "建议休息、散步，或只做轻松恢复活动。"
    elif band == "low":
        status = "cautious"
        summary = "今天恢复一般，适合轻松训练，不适合硬顶强度。"
        recommendation = "建议轻松跑、轻松骑，或者缩短训练时长。"
    elif band == "high":
        status = "ready"
        summary = "今天恢复较好，可以考虑完成计划训练。"
        recommendation = "如果主观感觉也不错，可以按计划做中高质量训练。"

    rationale = [
        {
            "label": "training_readiness",
            "message": f"训练准备度 {readiness_score}，当前分档为 {band}。",
            "value": readiness_score,
        },
        {
            "label": "recovery_time",
            "message": f"Garmin 预计恢复时间约 {recovery_hours} 小时。",
            "value": recovery_hours,
        },
        {
            "label": "fitness_base",
            "message": f"长期体能基础不错，VO2Max 为 {vo2max_value}。",
            "value": vo2max_value,
        },
        {
            "label": "sleep_score",
            "message": f"昨晚睡眠分 {sleep_score}，恢复并不算完全失败，但也不够强势。",
            "value": sleep_score,
        },
    ]
    if load_balance_feedback:
        rationale.append(
            {
                "label": "load_balance",
                "message": f"训练负荷平衡反馈为 {load_balance_feedback}。",
                "value": load_balance_feedback,
            }
        )

    return {
        "status": status,
        "summary": summary,
        "recommendation": recommendation,
        "rationale": rationale,
    }


def _composite_health_guidance(
    sleep_score: Any,
    avg_overnight_hrv: Any,
    avg_stress_level: Any,
    resting_heart_rate: Any,
    readiness_score: Any,
    recovery_time_hours: Any,
    vo2max_value: Any,
    recent_activity_summary: dict[str, Any],
    activity_structure: dict[str, Any],
    activity_count: int,
) -> dict[str, Any]:
    band = _readiness_guidance_band(readiness_score)
    status = "neutral"
    summary = "最近状态中等，能练但需要控制节奏。"
    recommendation = "建议按体感安排，优先保证恢复。"

    if band == "very_low" or (isinstance(recovery_time_hours, (int, float)) and recovery_time_hours >= 36):
        status = "fatigued"
        summary = "最近整体更像是累积疲劳偏高，不是体能差，而是恢复跟不上。"
        recommendation = "建议先减量 1-2 天，以休息、散步、轻松活动为主。"
    elif band in {"low", "moderate"}:
        status = "managed"
        summary = "最近有一定疲劳，但还没到完全不能练的程度。"
        recommendation = "建议保留训练频率，但把强度和总量压一压。"
    elif band == "high":
        status = "fresh"
        summary = "最近整体恢复不错，可以正常推进训练。"
        recommendation = "可继续执行计划训练，但仍要留意睡眠和主观疲劳。"

    latest_name = recent_activity_summary.get("latest_activity_name")
    latest_distance_km = recent_activity_summary.get("latest_activity_distance_km")
    latest_duration_hours = recent_activity_summary.get("latest_activity_duration_hours")

    rationale = [
        {
            "label": "readiness",
            "message": f"训练准备度 {readiness_score}，分档为 {band}。",
            "value": readiness_score,
        },
        {
            "label": "recovery_time",
            "message": f"恢复时间仍有约 {recovery_time_hours} 小时。",
            "value": recovery_time_hours,
        },
        {
            "label": "sleep_recovery",
            "message": f"睡眠分 {sleep_score}，隔夜 HRV {avg_overnight_hrv}。",
            "value": {"sleep_score": sleep_score, "avg_overnight_hrv": avg_overnight_hrv},
        },
        {
            "label": "fitness_base",
            "message": f"长期体能基础依然不错，静息心率 {resting_heart_rate}，VO2Max {vo2max_value}。",
            "value": {"resting_heart_rate": resting_heart_rate, "vo2max_value": vo2max_value},
        },
        {
            "label": "stress",
            "message": f"平均压力 {avg_stress_level}。",
            "value": avg_stress_level,
        },
    ]
    if latest_name:
        rationale.append(
            {
                "label": "recent_load",
                "message": f"最近一次训练是 {latest_name}，约 {latest_distance_km} km，持续 {latest_duration_hours} 小时；近 {activity_count} 天共记录 {activity_count} 次活动。",
                "value": recent_activity_summary,
            }
        )

    if activity_structure.get("mostly_endurance") and not activity_structure.get("has_recorded_strength"):
        rationale.append(
            {
                "label": "training_structure",
                "message": "最近记录几乎都是跑步/骑行这类耐力训练，暂未看到力量训练记录；这不一定马上出问题，但长期可能让力量支撑、核心稳定和疲劳下的动作控制变差。恢复上来后，可以补 1 次轻力量或核心训练。",
                "value": activity_structure,
            }
        )

    return {
        "status": status,
        "summary": summary,
        "recommendation": recommendation,
        "rationale": rationale,
    }


def _activity_history_guidance(
    activities: list[dict[str, Any]],
    activity_structure: dict[str, Any],
    recent_activity_summary: dict[str, Any],
) -> dict[str, Any]:
    activity_count = len(activities)
    status = "mixed"
    summary = "最近训练以耐力项目为主。"
    recommendation = "可以根据目标决定是继续堆耐力，还是补一点力量/核心。"

    if activity_structure.get("mostly_endurance") and not activity_structure.get("has_recorded_strength"):
        status = "endurance_heavy"
        summary = "最近训练结构明显偏耐力，有跑步和骑行，但暂未看到力量训练记录。"
        recommendation = "如果你不是在纯备赛冲量，恢复允许的话可以补 1 次轻力量或核心，帮助维持力量支撑和稳定性。"

    rationale = [
        {
            "label": "activity_count",
            "message": f"近窗口期共记录 {activity_count} 次活动。",
            "value": activity_count,
        },
        {
            "label": "activity_structure",
            "message": "最近活动类型以耐力项目为主；如果长期缺少力量或核心补充，后面更容易出现稳定性下降、动作散掉或疲劳时更难顶住。",
            "value": activity_structure,
        },
    ]
    if recent_activity_summary.get("latest_activity_name"):
        rationale.append(
            {
                "label": "latest_activity",
                "message": f"最近一次活动是 {recent_activity_summary.get('latest_activity_name')}，约 {recent_activity_summary.get('latest_activity_distance_km')} km，持续 {recent_activity_summary.get('latest_activity_duration_hours')} 小时。",
                "value": recent_activity_summary,
            }
        )

    return {
        "status": status,
        "summary": summary,
        "recommendation": recommendation,
        "rationale": rationale,
    }


def build_query_result(
    question_type: str,
    raw_result: dict[str, Any],
    *,
    target_date: date,
    display_name: Optional[str],
    full_name: Optional[str],
) -> dict[str, Any]:
    builders = {
        "sleep_recovery": _build_sleep_recovery,
        "training_state": _build_training_state,
        "activity_history": _build_activity_history,
        "performance_prediction": _build_performance_prediction,
        "composite_health": _build_composite_health,
    }
    try:
        builder = builders[question_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported question_type: {question_type}") from exc

    return builder(
        raw_result,
        target_date=target_date,
        display_name=display_name,
        full_name=full_name,
    )


def _base_meta(
    *,
    question_type: str,
    target_date: date,
    display_name: Optional[str],
    full_name: Optional[str],
    data_sources: list[str],
    source_window: dict[str, Any],
) -> dict[str, Any]:
    return {
        "question_type": question_type,
        "fetched_at": _iso_now(),
        "collected_for_date": target_date.isoformat(),
        "display_name": display_name,
        "full_name": full_name,
        "data_sources": data_sources,
        "source_window": source_window,
    }


def _build_sleep_recovery(
    raw_result: dict[str, Any],
    *,
    target_date: date,
    display_name: Optional[str],
    full_name: Optional[str],
) -> dict[str, Any]:
    sleep = raw_result.get("sleep_today", {}) or {}
    stress = raw_result.get("stress_today", {}) or {}
    respiration = raw_result.get("respiration_today", {}) or {}
    heart = raw_result.get("heart_rates_today", {}) or {}

    data = {
        "daily_wellness": {
            "sleep": {
                "calendar_date": _dig(sleep, "dailySleepDTO.calendarDate"),
                "sleep_time_seconds": _dig(sleep, "dailySleepDTO.sleepTimeSeconds"),
                "deep_sleep_seconds": _dig(sleep, "dailySleepDTO.deepSleepSeconds"),
                "light_sleep_seconds": _dig(sleep, "dailySleepDTO.lightSleepSeconds"),
                "rem_sleep_seconds": _dig(sleep, "dailySleepDTO.remSleepSeconds"),
                "sleep_score": _dig(sleep, "dailySleepDTO.sleepScores.overall.value"),
                "avg_sleep_stress": _dig(sleep, "dailySleepDTO.avgSleepStress"),
                "avg_sleep_heart_rate": _dig(sleep, "dailySleepDTO.avgHeartRate"),
                "avg_overnight_hrv": sleep.get("avgOvernightHrv"),
                "hrv_status": _dig(sleep, "hrvStatus.status"),
                "body_battery_change": sleep.get("bodyBatteryChange"),
            },
            "stress": {
                "calendar_date": stress.get("calendarDate"),
                "avg_stress_level": stress.get("avgStressLevel"),
                "max_stress_level": stress.get("maxStressLevel"),
            },
            "respiration": {
                "calendar_date": respiration.get("calendarDate"),
                "lowest_respiration_value": respiration.get("lowestRespirationValue"),
                "highest_respiration_value": respiration.get("highestRespirationValue"),
                "avg_waking_respiration_value": respiration.get("avgWakingRespirationValue"),
                "avg_sleep_respiration_value": respiration.get("avgSleepRespirationValue"),
            },
            "heart_rate": {
                "calendar_date": heart.get("calendarDate"),
                "resting_heart_rate": heart.get("restingHeartRate"),
                "last_seven_days_avg_resting_heart_rate": heart.get("lastSevenDaysAvgRestingHeartRate"),
                "min_heart_rate": heart.get("minHeartRate"),
                "max_heart_rate": heart.get("maxHeartRate"),
            },
        }
    }

    return {
        "meta": _base_meta(
            question_type="sleep_recovery",
            target_date=target_date,
            display_name=display_name,
            full_name=full_name,
            data_sources=["sleep_today", "stress_today", "respiration_today", "heart_rates_today"],
            source_window={"target_date": target_date.isoformat()},
        ),
        "question_type": "sleep_recovery",
        "data": data,
        "highlights": {
            "sleep_score": _dig(sleep, "dailySleepDTO.sleepScores.overall.value"),
            "sleep_time_seconds": _dig(sleep, "dailySleepDTO.sleepTimeSeconds"),
            "sleep_time_hours": _seconds_to_hours(_dig(sleep, "dailySleepDTO.sleepTimeSeconds")),
            "avg_overnight_hrv": sleep.get("avgOvernightHrv"),
            "body_battery_change": sleep.get("bodyBatteryChange"),
            "avg_stress_level": stress.get("avgStressLevel"),
            "resting_heart_rate": heart.get("restingHeartRate"),
        },
        "missing": _collect_missing(
            raw_result,
            {
                "sleep_today": ["dailySleepDTO.sleepTimeSeconds", "dailySleepDTO.sleepScores.overall.value"],
                "stress_today": ["avgStressLevel"],
                "respiration_today": ["avgSleepRespirationValue"],
                "heart_rates_today": ["restingHeartRate"],
            },
        ),
    }


def _build_training_state(
    raw_result: dict[str, Any],
    *,
    target_date: date,
    display_name: Optional[str],
    full_name: Optional[str],
) -> dict[str, Any]:
    readiness = raw_result.get("training_readiness_today", []) or []
    readiness0 = readiness[0] if readiness and isinstance(readiness[0], dict) else {}
    status = raw_result.get("training_status_today", {}) or {}
    sleep = raw_result.get("sleep_today", {}) or {}

    data = {
        "training_state": {
            "training_readiness": {
                "calendar_date": readiness0.get("calendarDate"),
                "level": readiness0.get("level"),
                "score": readiness0.get("score"),
                "sleep_score": readiness0.get("sleepScore"),
                "recovery_time_minutes": readiness0.get("recoveryTime"),
                "acute_load": readiness0.get("acuteLoad"),
                "hrv_weekly_average": readiness0.get("hrvWeeklyAverage"),
            },
            "training_status": {
                "vo2max_calendar_date": _dig(status, "mostRecentVO2Max.generic.calendarDate"),
                "vo2max_value": _dig(status, "mostRecentVO2Max.generic.vo2MaxValue"),
                "vo2max_precise_value": _dig(status, "mostRecentVO2Max.generic.vo2MaxPreciseValue"),
                "load_balance_feedback": _extract_first_nested_value(
                    _dig(status, "mostRecentTrainingLoadBalance.metricsTrainingLoadBalanceDTOMap"),
                    "trainingBalanceFeedbackPhrase",
                ),
                "training_status": _extract_first_nested_value(
                    _dig(status, "mostRecentTrainingStatus.latestTrainingStatusData"),
                    "trainingStatus",
                ),
            },
            "supporting_sleep": {
                "sleep_score": _dig(sleep, "dailySleepDTO.sleepScores.overall.value"),
                "sleep_time_seconds": _dig(sleep, "dailySleepDTO.sleepTimeSeconds"),
                "avg_overnight_hrv": sleep.get("avgOvernightHrv"),
            },
        }
    }

    return {
        "meta": _base_meta(
            question_type="training_state",
            target_date=target_date,
            display_name=display_name,
            full_name=full_name,
            data_sources=["training_readiness_today", "training_status_today", "sleep_today"],
            source_window={"target_date": target_date.isoformat()},
        ),
        "question_type": "training_state",
        "data": data,
        "highlights": {
            "training_readiness_level": readiness0.get("level"),
            "training_readiness_score": readiness0.get("score"),
            "training_readiness_band": _readiness_guidance_band(readiness0.get("score")),
            "sleep_score": readiness0.get("sleepScore"),
            "recovery_time_minutes": readiness0.get("recoveryTime"),
            "recovery_time_hours": _minutes_to_hours(readiness0.get("recoveryTime")),
            "vo2max_value": _dig(status, "mostRecentVO2Max.generic.vo2MaxValue"),
            "load_balance_feedback": _extract_first_nested_value(
                _dig(status, "mostRecentTrainingLoadBalance.metricsTrainingLoadBalanceDTOMap"),
                "trainingBalanceFeedbackPhrase",
            ),
        },
        "guidance": _training_state_guidance(
            readiness0.get("score"),
            readiness0.get("recoveryTime"),
            readiness0.get("sleepScore"),
            _dig(status, "mostRecentVO2Max.generic.vo2MaxValue"),
            _extract_first_nested_value(
                _dig(status, "mostRecentTrainingLoadBalance.metricsTrainingLoadBalanceDTOMap"),
                "trainingBalanceFeedbackPhrase",
            ),
        ),
        "missing": _collect_missing(
            raw_result,
            {
                "training_readiness_today": ["0.score", "0.level"],
                "training_status_today": ["mostRecentVO2Max.generic.vo2MaxValue"],
                "sleep_today": ["dailySleepDTO.sleepScores.overall.value"],
            },
        ),
    }


def _build_activity_history(
    raw_result: dict[str, Any],
    *,
    target_date: date,
    display_name: Optional[str],
    full_name: Optional[str],
) -> dict[str, Any]:
    activities = raw_result.get("activities_last_n_days", []) or []
    window_days = raw_result.get("window_days")
    window_start = raw_result.get("window_start")
    window_end = raw_result.get("window_end")

    recent_activities = [
        {
            "activity_id": activity.get("activityId"),
            "activity_name": activity.get("activityName"),
            "activity_type": _dig(activity, "activityType.typeKey"),
            "start_time_local": activity.get("startTimeLocal"),
            "distance_meters": activity.get("distance"),
            "duration_seconds": activity.get("duration"),
            "average_heart_rate": activity.get("averageHR"),
            "calories": activity.get("calories"),
        }
        for activity in activities[:20]
        if isinstance(activity, dict)
    ]
    activity_structure = _activity_structure_summary(recent_activities)
    latest_summary = _latest_activity_summary(recent_activities)

    data = {
        "recent_activities": {
            "count": len(activities),
            "window_days": window_days,
            "window_start": window_start,
            "window_end": window_end,
            "items": recent_activities,
            "structure": activity_structure,
        }
    }

    first = recent_activities[0] if recent_activities else {}
    return {
        "meta": _base_meta(
            question_type="activity_history",
            target_date=target_date,
            display_name=display_name,
            full_name=full_name,
            data_sources=["activities_last_n_days"],
            source_window={
                "target_date": target_date.isoformat(),
                "window_days": window_days,
                "window_start": window_start,
                "window_end": window_end,
            },
        ),
        "question_type": "activity_history",
        "data": data,
        "highlights": {
            "activity_count": len(activities),
            "latest_activity_name": first.get("activity_name"),
            "latest_activity_type": first.get("activity_type"),
            "latest_activity_distance_meters": first.get("distance_meters"),
            "latest_activity_distance_km": _round_or_none(
                (first.get("distance_meters") or 0) / 1000 if first.get("distance_meters") is not None else None
            ),
            "latest_activity_duration_seconds": first.get("duration_seconds"),
            "latest_activity_duration_hours": _seconds_to_hours(first.get("duration_seconds")),
            "activity_structure": activity_structure,
        },
        "guidance": _activity_history_guidance(recent_activities, activity_structure, latest_summary),
        "missing": [] if activities else ["activities_last_n_days"],
    }


def _build_performance_prediction(
    raw_result: dict[str, Any],
    *,
    target_date: date,
    display_name: Optional[str],
    full_name: Optional[str],
) -> dict[str, Any]:
    prediction = raw_result.get("race_predictions_latest", {}) or {}
    status = raw_result.get("training_status_today", {}) or {}

    data = {
        "performance_prediction": {
            "race_predictions": {
                "calendar_date": prediction.get("calendarDate"),
                "time_5k_seconds": prediction.get("time5K"),
                "time_10k_seconds": prediction.get("time10K"),
                "time_half_marathon_seconds": prediction.get("timeHalfMarathon"),
                "time_marathon_seconds": prediction.get("timeMarathon"),
            },
            "supporting_training_status": {
                "vo2max_calendar_date": _dig(status, "mostRecentVO2Max.generic.calendarDate"),
                "vo2max_value": _dig(status, "mostRecentVO2Max.generic.vo2MaxValue"),
                "vo2max_precise_value": _dig(status, "mostRecentVO2Max.generic.vo2MaxPreciseValue"),
                "load_balance_feedback": _extract_first_nested_value(
                    _dig(status, "mostRecentTrainingLoadBalance.metricsTrainingLoadBalanceDTOMap"),
                    "trainingBalanceFeedbackPhrase",
                ),
            },
        }
    }

    return {
        "meta": _base_meta(
            question_type="performance_prediction",
            target_date=target_date,
            display_name=display_name,
            full_name=full_name,
            data_sources=["race_predictions_latest", "training_status_today"],
            source_window={"target_date": target_date.isoformat()},
        ),
        "question_type": "performance_prediction",
        "data": data,
        "highlights": {
            "time_5k_seconds": prediction.get("time5K"),
            "time_10k_seconds": prediction.get("time10K"),
            "time_half_marathon_seconds": prediction.get("timeHalfMarathon"),
            "time_marathon_seconds": prediction.get("timeMarathon"),
            "vo2max_value": _dig(status, "mostRecentVO2Max.generic.vo2MaxValue"),
            "time_5k_minutes": _seconds_to_minutes(prediction.get("time5K")),
            "time_half_marathon_hours": _seconds_to_hours(prediction.get("timeHalfMarathon")),
        },
        "missing": _collect_missing(
            raw_result,
            {
                "race_predictions_latest": ["timeHalfMarathon", "timeMarathon"],
                "training_status_today": ["mostRecentVO2Max.generic.vo2MaxValue"],
            },
        ),
    }


def _build_composite_health(
    raw_result: dict[str, Any],
    *,
    target_date: date,
    display_name: Optional[str],
    full_name: Optional[str],
) -> dict[str, Any]:
    sleep = raw_result.get("sleep_today", {}) or {}
    stress = raw_result.get("stress_today", {}) or {}
    heart = raw_result.get("heart_rates_today", {}) or {}
    readiness = raw_result.get("training_readiness_today", []) or []
    readiness0 = readiness[0] if readiness and isinstance(readiness[0], dict) else {}
    status = raw_result.get("training_status_today", {}) or {}
    activities = raw_result.get("activities_last_n_days", []) or []
    window_days = raw_result.get("window_days")
    window_start = raw_result.get("window_start")
    window_end = raw_result.get("window_end")

    recent_activities = [
        {
            "activity_id": activity.get("activityId"),
            "activity_name": activity.get("activityName"),
            "activity_type": _dig(activity, "activityType.typeKey"),
            "start_time_local": activity.get("startTimeLocal"),
            "distance_meters": activity.get("distance"),
            "duration_seconds": activity.get("duration"),
            "average_heart_rate": activity.get("averageHR"),
        }
        for activity in activities[:10]
        if isinstance(activity, dict)
    ]
    activity_structure = _activity_structure_summary(recent_activities)
    latest_summary = _latest_activity_summary(recent_activities)

    data = {
        "composite_health": {
            "sleep": {
                "sleep_score": _dig(sleep, "dailySleepDTO.sleepScores.overall.value"),
                "sleep_time_seconds": _dig(sleep, "dailySleepDTO.sleepTimeSeconds"),
                "avg_overnight_hrv": sleep.get("avgOvernightHrv"),
                "body_battery_change": sleep.get("bodyBatteryChange"),
            },
            "stress": {
                "avg_stress_level": stress.get("avgStressLevel"),
                "max_stress_level": stress.get("maxStressLevel"),
            },
            "heart_rate": {
                "resting_heart_rate": heart.get("restingHeartRate"),
                "last_seven_days_avg_resting_heart_rate": heart.get("lastSevenDaysAvgRestingHeartRate"),
            },
            "training_readiness": {
                "level": readiness0.get("level"),
                "score": readiness0.get("score"),
                "recovery_time_minutes": readiness0.get("recoveryTime"),
                "acute_load": readiness0.get("acuteLoad"),
            },
            "training_status": {
                "vo2max_value": _dig(status, "mostRecentVO2Max.generic.vo2MaxValue"),
                "load_balance_feedback": _extract_first_nested_value(
                    _dig(status, "mostRecentTrainingLoadBalance.metricsTrainingLoadBalanceDTOMap"),
                    "trainingBalanceFeedbackPhrase",
                ),
            },
            "recent_activities": {
                "count": len(activities),
                "window_days": window_days,
                "window_start": window_start,
                "window_end": window_end,
                "items": recent_activities,
                "structure": activity_structure,
            },
        }
    }

    return {
        "meta": _base_meta(
            question_type="composite_health",
            target_date=target_date,
            display_name=display_name,
            full_name=full_name,
            data_sources=[
                "sleep_today",
                "stress_today",
                "heart_rates_today",
                "training_readiness_today",
                "training_status_today",
                "activities_last_n_days",
            ],
            source_window={
                "target_date": target_date.isoformat(),
                "window_days": window_days,
                "window_start": window_start,
                "window_end": window_end,
            },
        ),
        "question_type": "composite_health",
        "data": data,
        "highlights": {
            "sleep_score": _dig(sleep, "dailySleepDTO.sleepScores.overall.value"),
            "sleep_time_hours": _seconds_to_hours(_dig(sleep, "dailySleepDTO.sleepTimeSeconds")),
            "avg_overnight_hrv": sleep.get("avgOvernightHrv"),
            "avg_stress_level": stress.get("avgStressLevel"),
            "resting_heart_rate": heart.get("restingHeartRate"),
            "training_readiness_score": readiness0.get("score"),
            "training_readiness_band": _readiness_guidance_band(readiness0.get("score")),
            "recovery_time_hours": _minutes_to_hours(readiness0.get("recoveryTime")),
            "vo2max_value": _dig(status, "mostRecentVO2Max.generic.vo2MaxValue"),
            "activity_count": len(activities),
            "recent_activity_summary": latest_summary,
            "activity_structure": activity_structure,
        },
        "guidance": _composite_health_guidance(
            _dig(sleep, "dailySleepDTO.sleepScores.overall.value"),
            sleep.get("avgOvernightHrv"),
            stress.get("avgStressLevel"),
            heart.get("restingHeartRate"),
            readiness0.get("score"),
            _minutes_to_hours(readiness0.get("recoveryTime")),
            _dig(status, "mostRecentVO2Max.generic.vo2MaxValue"),
            latest_summary,
            activity_structure,
            len(activities),
        ),
        "missing": _collect_missing(
            raw_result,
            {
                "sleep_today": ["dailySleepDTO.sleepScores.overall.value"],
                "stress_today": ["avgStressLevel"],
                "heart_rates_today": ["restingHeartRate"],
                "training_readiness_today": ["0.score"],
                "training_status_today": ["mostRecentVO2Max.generic.vo2MaxValue"],
            },
        ),
    }


def _extract_first_nested_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        for nested in value.values():
            if isinstance(nested, dict) and key in nested:
                return nested.get(key)
    return None
