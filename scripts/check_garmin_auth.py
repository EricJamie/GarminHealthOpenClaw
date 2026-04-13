#!/usr/bin/env python3
"""Read-only validation for GARMIN_TOKEN_DATA authentication."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.garmin_auth import GarminClient
from app.garmin_auth.config import GarminAuthConfig


def main() -> None:
    config = GarminAuthConfig.from_env()
    if not config.token_data:
        raise SystemExit("GARMIN_TOKEN_DATA is not set in the environment or .env")

    client = GarminClient(
        token_data=config.token_data,
        email="",
        password="",
    )
    profile = {
        "display_name": client.client.display_name,
        "full_name": client.client.full_name,
    }
    print(json.dumps({"ok": True, "profile": profile}, ensure_ascii=False))


if __name__ == "__main__":
    main()
