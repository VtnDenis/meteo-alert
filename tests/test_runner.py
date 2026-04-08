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
    }


def test_run_monitoring_sends_email_when_rain_detected(monkeypatch: pytest.MonkeyPatch) -> None:
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
                    precipitation_mm=0.7,
                    coverage_id="open-meteo:auto",
                    run_time_utc=datetime(2026, 4, 11, 5, 0, tzinfo=timezone.utc),
                )
            ]

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
    monkeypatch.setattr("src.runner.ResendEmailService", _FakeEmailService)

    now_utc = datetime(2026, 4, 11, 6, 0, tzinfo=timezone.utc)
    result = run_monitoring(config=config, now_utc=now_utc)

    assert result.status == "sent"
    assert result.sent_email_id == "email_123"
    assert len(result.rainy_hours_local) == 1


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