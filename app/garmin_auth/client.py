"""Project auth entrypoint built on the vendored Garmin client."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from .config import GarminAuthConfig
from .vendor.garmin_client import GarminClient as VendoredGarminClient

logger = logging.getLogger(__name__)


class GarminTokenExpiredError(RuntimeError):
    """Raised when the provided Garmin token data is no longer usable."""


class GarminAuthClient:
    """
    Project-level auth wrapper around the vendored Garmin login client.

    Runtime preference is always:
    1. ``GARMIN_TOKEN_DATA`` or explicit ``token_data``
    2. ``GARMIN_EMAIL`` + ``GARMIN_PASSWORD`` only as bootstrap/refresh fallback
    """

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        token_data: str | None = None,
        prompt_mfa: Optional[Callable[[], str]] = None,
    ) -> None:
        env_config = GarminAuthConfig.from_env()
        self.email = email if email is not None else env_config.email
        self.password = password if password is not None else env_config.password
        self.token_data = token_data if token_data is not None else env_config.token_data
        self.prompt_mfa = prompt_mfa
        self._client: VendoredGarminClient | None = None

        self._connect()

    @classmethod
    def from_env(
        cls,
        prompt_mfa: Optional[Callable[[], str]] = None,
    ) -> "GarminAuthClient":
        return cls(prompt_mfa=prompt_mfa)

    def _new_client(self) -> VendoredGarminClient:
        return VendoredGarminClient()

    def _login_with_token_data(self) -> None:
        logger.info("Authenticating to Garmin with token data")
        client = self._new_client()
        client.loads(self.token_data or "")
        client._load_profile()
        self._client = client
        logger.info("Garmin token-data authentication succeeded")

    def _login_with_password(self) -> None:
        logger.info("Authenticating to Garmin with email/password bootstrap flow")
        client = self._new_client()
        client.login(self.email or "", self.password or "", prompt_mfa=self.prompt_mfa)
        self._client = client
        logger.info("Garmin credential bootstrap succeeded")

    def _connect(self) -> None:
        if self.token_data:
            try:
                self._login_with_token_data()
                return
            except Exception as exc:
                if self.email and self.password:
                    logger.warning(
                        "Garmin token data was unusable; falling back to credential bootstrap: %s",
                        exc,
                    )
                else:
                    raise self._wrap_token_error(exc) from exc

        if self.email and self.password:
            self._login_with_password()
            return

        raise ValueError(
            "Garmin authentication requires GARMIN_TOKEN_DATA, or GARMIN_EMAIL plus GARMIN_PASSWORD."
        )

    @staticmethod
    def _wrap_token_error(exc: Exception) -> GarminTokenExpiredError:
        return GarminTokenExpiredError(f"Garmin token data is expired or invalid: {exc}")

    @property
    def client(self) -> VendoredGarminClient:
        if self._client is None:
            raise RuntimeError("Garmin client is not connected")
        return self._client

    def export_token_data(self) -> str:
        return self.client.dumps()


# Backward-compatible alias for scripts that expect GarminClient.
GarminClient = GarminAuthClient
