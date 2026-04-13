#!/usr/bin/env python3
"""Acquire Garmin token data for local use and optionally persist it to .env."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.garmin_auth import GarminClient


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


def _prompt_mfa() -> str:
    return input("Enter Garmin MFA code: ").strip()


def _quote_env_value(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _write_env_token(env_path: Path, token_data: str) -> None:
    line = f"GARMIN_TOKEN_DATA={_quote_env_value(token_data)}"
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    replaced = False
    new_lines = []
    for existing in lines:
        if existing.startswith("GARMIN_TOKEN_DATA="):
            new_lines.append(line)
            replaced = True
        else:
            new_lines.append(existing)

    if not replaced:
        if new_lines and new_lines[-1] != "":
            new_lines.append("")
        new_lines.append(line)

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Acquire Garmin token data")
    parser.add_argument("--garmin-email", default=None, help="Garmin email")
    parser.add_argument("--garmin-password", default=None, help="Garmin password")
    parser.add_argument("--garmin-token-data", default=None, help="Existing Garmin token JSON")
    parser.add_argument(
        "--write-env",
        action="store_true",
        help="Write the resulting GARMIN_TOKEN_DATA back to the .env file",
    )
    parser.add_argument(
        "--env-file",
        default=str(DEFAULT_ENV_PATH),
        help="Path to the .env file to update when --write-env is used",
    )
    args = parser.parse_args()

    client = GarminClient(
        email=args.garmin_email,
        password=args.garmin_password,
        token_data=args.garmin_token_data,
        prompt_mfa=_prompt_mfa,
    )
    token_data = client.export_token_data()
    if args.write_env:
        _write_env_token(Path(args.env_file), token_data)
    print(token_data)


if __name__ == "__main__":
    main()
