#!/usr/bin/env python3
"""Question-driven Garmin CLI for OpenClaw local skill integration."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.context import build_query_result
from app.garmin_auth import GarminClient
from app.garmin_auth.config import GarminAuthConfig
from app.query import SUPPORTED_QUERY_TYPES, GarminQueryService


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a Garmin question-driven local query")
    parser.add_argument(
        "question_type",
        choices=SUPPORTED_QUERY_TYPES,
        help="Structured question type to execute",
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Target date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Window size for history-based queries",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON response",
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Include raw Garmin responses for local debugging",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    config = GarminAuthConfig.from_env()
    if not config.token_data and not (config.email and config.password):
        raise SystemExit(
            "Garmin authentication is not configured. Set GARMIN_TOKEN_DATA, or GARMIN_EMAIL plus GARMIN_PASSWORD."
        )

    target_date = date.fromisoformat(args.date)
    auth_client = GarminClient.from_env()
    service = GarminQueryService(auth_client)
    raw_result = service.run(args.question_type, target_date=target_date, days=args.days)
    query_result = build_query_result(
        args.question_type,
        raw_result,
        target_date=target_date,
        display_name=getattr(auth_client.client, "display_name", None),
        full_name=getattr(auth_client.client, "full_name", None),
    )
    if args.include_raw:
        query_result["raw_data"] = raw_result

    indent = 2 if args.pretty else None
    print(json.dumps(query_result, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main()
