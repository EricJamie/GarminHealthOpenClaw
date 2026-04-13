"""Environment-backed configuration for the Garmin auth layer."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _clean_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


@dataclass(frozen=True)
class GarminAuthConfig:
    """Resolved Garmin auth inputs for the current process."""

    token_data: str | None = None
    email: str | None = None
    password: str | None = None

    @classmethod
    def from_env(cls) -> "GarminAuthConfig":
        return cls(
            token_data=_clean_env("GARMIN_TOKEN_DATA"),
            email=_clean_env("GARMIN_EMAIL"),
            password=_clean_env("GARMIN_PASSWORD"),
        )
