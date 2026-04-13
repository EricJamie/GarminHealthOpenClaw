"""Minimal tests for the Garmin auth boundary."""

from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.garmin_auth.client import GarminAuthClient
from app.garmin_auth.vendor.garmin_client import GarminClient as VendoredGarminClient
from app.garmin_auth.vendor.garmin_client.constants import (
    LOGIN_DELAY_MAX_S,
    LOGIN_DELAY_MIN_S,
)
from scripts.refresh_garmin_token import _write_env_token


class _FakeVendoredClient:
    def __init__(self) -> None:
        self.loaded_token_data = None

    def loads(self, tokenstore: str) -> None:
        self.loaded_token_data = tokenstore

    def _load_profile(self) -> None:
        return None

    def dumps(self) -> str:
        return self.loaded_token_data or ""


class GarminAuthClientTests(unittest.TestCase):
    def test_token_data_path_uses_vendored_client(self) -> None:
        with patch("app.garmin_auth.client.VendoredGarminClient", _FakeVendoredClient):
            client = GarminAuthClient(token_data='{"di_token":"a","di_refresh_token":"b","di_client_id":"c"}')

        self.assertIsInstance(client.client, _FakeVendoredClient)
        self.assertEqual(client.export_token_data(), '{"di_token":"a","di_refresh_token":"b","di_client_id":"c"}')

    def test_token_data_takes_priority_over_credentials(self) -> None:
        with patch("app.garmin_auth.client.VendoredGarminClient", _FakeVendoredClient):
            with patch.object(GarminAuthClient, "_login_with_password") as password_login:
                client = GarminAuthClient(
                    token_data='{"di_token":"a","di_refresh_token":"b","di_client_id":"c"}',
                    email="runner@example.com",
                    password="secret",
                )

        self.assertIsInstance(client.client, _FakeVendoredClient)
        password_login.assert_not_called()

    def test_wrapper_binds_to_vendored_module(self) -> None:
        self.assertEqual(VendoredGarminClient.__module__, "app.garmin_auth.vendor.garmin_client.client")

    def test_wrapper_source_does_not_import_non_vendored_login_libraries(self) -> None:
        source = inspect.getsource(inspect.getmodule(GarminAuthClient))
        self.assertNotIn("import garth", source)
        self.assertNotIn("from garth", source)
        self.assertNotIn("import garminconnect", source)
        self.assertNotIn("from garminconnect", source)

    def test_login_delay_guardrails_match_adr_contract(self) -> None:
        self.assertEqual(LOGIN_DELAY_MIN_S, 30.0)
        self.assertEqual(LOGIN_DELAY_MAX_S, 45.0)

    def test_write_env_token_replaces_existing_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("GARMIN_TOKEN_DATA='old'\nGARMIN_EMAIL='runner@example.com'\n", encoding="utf-8")

            _write_env_token(env_path, '{"di_token":"a"}')

            content = env_path.read_text(encoding="utf-8")
            self.assertIn('GARMIN_TOKEN_DATA=\'{"di_token":"a"}\'', content)
            self.assertIn("GARMIN_EMAIL='runner@example.com'", content)


if __name__ == "__main__":
    unittest.main()
