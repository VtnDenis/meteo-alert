from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

import pytest

from src.config import AppConfig
from src.open_meteo_client import ForecastPoint
from src.runner import run_monitoring


def _base_env() -> dict[str, str]:
    return {
        "RESEND_API_KEY": "dummy",
        "RESEND_FROM": "alerts@example.com",
        "WHATSAPP_ACCESS_TOKEN": "token_123",
        "WHATSAPP_PHONE_NUMBER_ID": "1906385232743451",
        "WHATSAPP_BUSINESS_ACCOUNT_ID": "104996122399160",
    }


def test_run_monitoring_sends_whatsapp_when_rain_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    config = AppConfig.from_mapping(_base_env())

    class _FakeClient:
        def __init__(self, config: AppConfig) -> None:
            self._config = config

        def fetch_slot_precipitations(
            self,
            slot_hours_utc: Sequence[datetime],
            lat: float,
            lon: float,
        ) -> list[ForecastPoint]:
            return [
                ForecastPoint(
                    forecast_time_utc=slot_hours_utc[0],
                    precipitation_mm=1.0,
                    coverage_id="open-meteo:auto",
                    run_time_utc=datetime(2026, 4, 11, 5, 0, tzinfo=timezone.utc),
                )
            ]

    class _FakeWhatsAppService:
        def __init__(
            self,
            access_token: str,
            phone_number_id: str,
            recipient_phone_number: str,
            template_name: str,
            template_language: str,
            graph_api_version: str = "v25.0",
            timeout_seconds: float = 20.0,
        ) -> None:
            self._access_token = access_token
            self._phone_number_id = phone_number_id
            self._recipient_phone_number = recipient_phone_number
            self._template_name = template_name
            self._template_language = template_language
            self._graph_api_version = graph_api_version
            self._timeout_seconds = timeout_seconds

        def send(self, content: object, idempotency_key: str) -> str:
            assert idempotency_key == "meteo-alert/2026-04-11/morning"
            return "wamid_123"

    class _FailIfCalledEmailService:
        def __init__(
            self,
            api_key: str,
            from_email: str,
            to_email: str,
            timeout_seconds: float = 20.0,
        ) -> None:
            self._api_key = api_key
            self._from_email = from_email
            self._to_email = to_email
            self._timeout_seconds = timeout_seconds

        def send(self, content: object, idempotency_key: str) -> str:
            raise AssertionError("Email fallback should not be used when WhatsApp succeeds.")

    monkeypatch.setattr("src.runner.OpenMeteoClient", _FakeClient)
    monkeypatch.setattr("src.runner.MetaWhatsAppService", _FakeWhatsAppService)
    monkeypatch.setattr("src.runner.ResendEmailService", _FailIfCalledEmailService)

    now_utc = datetime(2026, 4, 11, 6, 0, tzinfo=timezone.utc)
    result = run_monitoring(config=config, now_utc=now_utc)

    assert result.status == "sent"
    assert result.sent_whatsapp_message_id == "wamid_123"
    assert result.sent_email_id is None
    assert len(result.rainy_hours_local) == 1


def test_run_monitoring_checks_target_date_before_it_happens(monkeypatch: pytest.MonkeyPatch) -> None:
    config = AppConfig.from_mapping(_base_env())

    class _FakeClient:
        def __init__(self, config: AppConfig) -> None:
            self._config = config

        def fetch_slot_precipitations(
            self,
            slot_hours_utc: Sequence[datetime],
            lat: float,
            lon: float,
        ) -> list[ForecastPoint]:
            return [
                ForecastPoint(
                    forecast_time_utc=slot_hours_utc[0],
                    precipitation_mm=1.0,
                    coverage_id="open-meteo:auto",
                    run_time_utc=datetime(2026, 4, 10, 0, 0, tzinfo=timezone.utc),
                )
            ]

    class _FakeWhatsAppService:
        def __init__(
            self,
            access_token: str,
            phone_number_id: str,
            recipient_phone_number: str,
            template_name: str,
            template_language: str,
            graph_api_version: str = "v25.0",
            timeout_seconds: float = 20.0,
        ) -> None:
            self._access_token = access_token
            self._phone_number_id = phone_number_id
            self._recipient_phone_number = recipient_phone_number
            self._template_name = template_name
            self._template_language = template_language
            self._graph_api_version = graph_api_version
            self._timeout_seconds = timeout_seconds

        def send(self, content: object, idempotency_key: str) -> str:
            assert idempotency_key == "meteo-alert/2026-04-11/morning"
            return "wamid_456"

    class _FailIfCalledEmailService:
        def __init__(
            self,
            api_key: str,
            from_email: str,
            to_email: str,
            timeout_seconds: float = 20.0,
        ) -> None:
            self._api_key = api_key
            self._from_email = from_email
            self._to_email = to_email
            self._timeout_seconds = timeout_seconds

        def send(self, content: object, idempotency_key: str) -> str:
            raise AssertionError("Email fallback should not be used when WhatsApp succeeds.")

    monkeypatch.setattr("src.runner.OpenMeteoClient", _FakeClient)
    monkeypatch.setattr("src.runner.MetaWhatsAppService", _FakeWhatsAppService)
    monkeypatch.setattr("src.runner.ResendEmailService", _FailIfCalledEmailService)

    now_utc = datetime(2026, 4, 10, 0, 0, tzinfo=timezone.utc)
    result = run_monitoring(config=config, now_utc=now_utc)

    assert result.status == "sent"
    assert result.slot is not None
    assert result.slot.value == "morning"
    assert result.sent_whatsapp_message_id == "wamid_456"
    assert result.sent_email_id is None


def test_run_monitoring_falls_back_to_email_when_whatsapp_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    config = AppConfig.from_mapping(_base_env())

    class _FakeClient:
        def __init__(self, config: AppConfig) -> None:
            self._config = config

        def fetch_slot_precipitations(
            self,
            slot_hours_utc: Sequence[datetime],
            lat: float,
            lon: float,
        ) -> list[ForecastPoint]:
            return [
                ForecastPoint(
                    forecast_time_utc=slot_hours_utc[0],
                    precipitation_mm=1.2,
                    coverage_id="open-meteo:auto",
                    run_time_utc=datetime(2026, 4, 11, 5, 0, tzinfo=timezone.utc),
                )
            ]

    class _FailingWhatsAppService:
        def __init__(
            self,
            access_token: str,
            phone_number_id: str,
            recipient_phone_number: str,
            template_name: str,
            template_language: str,
            graph_api_version: str = "v25.0",
            timeout_seconds: float = 20.0,
        ) -> None:
            self._access_token = access_token
            self._phone_number_id = phone_number_id
            self._recipient_phone_number = recipient_phone_number
            self._template_name = template_name
            self._template_language = template_language
            self._graph_api_version = graph_api_version
            self._timeout_seconds = timeout_seconds

        def send(self, content: object, idempotency_key: str) -> str:
            raise RuntimeError("template name does not exist")

    class _FakeEmailService:
        def __init__(
            self,
            api_key: str,
            from_email: str,
            to_email: str,
            timeout_seconds: float = 20.0,
        ) -> None:
            self._api_key = api_key
            self._from_email = from_email
            self._to_email = to_email
            self._timeout_seconds = timeout_seconds

        def send(self, content: object, idempotency_key: str) -> str:
            assert idempotency_key == "meteo-alert/2026-04-11/morning"
            return "email_123"

    monkeypatch.setattr("src.runner.OpenMeteoClient", _FakeClient)
    monkeypatch.setattr("src.runner.MetaWhatsAppService", _FailingWhatsAppService)
    monkeypatch.setattr("src.runner.ResendEmailService", _FakeEmailService)

    now_utc = datetime(2026, 4, 11, 6, 0, tzinfo=timezone.utc)
    result = run_monitoring(config=config, now_utc=now_utc)

    assert result.status == "sent"
    assert result.sent_whatsapp_message_id is None
    assert result.sent_email_id == "email_123"
    assert "fallback email sent" in result.detail


def test_run_monitoring_skips_when_no_rain(monkeypatch: pytest.MonkeyPatch) -> None:
    config = AppConfig.from_mapping(_base_env())

    class _FakeClient:
        def __init__(self, config: AppConfig) -> None:
            self._config = config

        def fetch_slot_precipitations(
            self,
            slot_hours_utc: Sequence[datetime],
            lat: float,
            lon: float,
        ) -> list[ForecastPoint]:
            return [
                ForecastPoint(
                    forecast_time_utc=slot_hours_utc[0],
                    precipitation_mm=0.0,
                    coverage_id="open-meteo:auto",
                    run_time_utc=datetime(2026, 4, 11, 5, 0, tzinfo=timezone.utc),
                )
            ]

    monkeypatch.setattr("src.runner.OpenMeteoClient", _FakeClient)

    now_utc = datetime(2026, 4, 11, 6, 0, tzinfo=timezone.utc)
    result = run_monitoring(config=config, now_utc=now_utc)

    assert result.status == "skip_no_rain"
    assert result.sent_email_id is None
    assert result.sent_whatsapp_message_id is None


def test_run_monitoring_skips_after_target_date() -> None:
    config = AppConfig.from_mapping(_base_env())

    now_utc = datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc)
    result = run_monitoring(config=config, now_utc=now_utc)

    assert result.status == "skip_out_of_target_date"
    assert result.detail == "Current local date is after TARGET_DATE."
