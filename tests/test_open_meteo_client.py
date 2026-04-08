from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
import requests

from src.config import AppConfig
from src.open_meteo_client import OpenMeteoClient


class _MockResponse:
    def __init__(self, status_code: int, payload: Any, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> Any:
        return self._payload


def _base_env() -> dict[str, str]:
    return {
        "RESEND_API_KEY": "dummy",
        "RESEND_FROM": "alerts@example.com",
    }


def _config() -> AppConfig:
    return AppConfig.from_mapping(_base_env())


def test_fetch_slot_precipitations_maps_requested_hours(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_params: dict[str, str] = {}

    def _fake_get(
        self: requests.Session,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
        timeout: float,
    ) -> _MockResponse:
        captured_params.update(params)
        assert url == "https://api.open-meteo.com/v1/forecast"
        assert headers["accept"] == "application/json"
        assert timeout == 30.0
        return _MockResponse(
            status_code=200,
            payload={
                "hourly": {
                    "time": [
                        "2026-04-11T04:00",
                        "2026-04-11T05:00",
                        "2026-04-11T06:00",
                    ],
                    "precipitation": [0.0, 1.25, 0.5],
                }
            },
        )

    monkeypatch.setattr(requests.Session, "get", _fake_get)

    client = OpenMeteoClient(_config())
    slot_hours = [
        datetime(2026, 4, 11, 5, 0, tzinfo=timezone.utc),
        datetime(2026, 4, 11, 6, 0, tzinfo=timezone.utc),
    ]
    points = client.fetch_slot_precipitations(slot_hours, lat=45.470463, lon=4.505748)

    assert captured_params["hourly"] == "precipitation"
    assert captured_params["timezone"] == "GMT"
    assert captured_params["models"] == "auto"
    assert captured_params["precipitation_unit"] == "mm"

    assert len(points) == 2
    assert points[0].precipitation_mm == 1.25
    assert points[1].precipitation_mm == 0.5
    assert points[0].coverage_id == "open-meteo:auto"
    assert points[0].run_time_utc.tzinfo is timezone.utc
    assert points[1].run_time_utc == points[0].run_time_utc


def test_fetch_slot_precipitations_raises_on_invalid_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_get(
        self: requests.Session,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
        timeout: float,
    ) -> _MockResponse:
        return _MockResponse(status_code=200, payload={"hourly": {"time": []}})

    monkeypatch.setattr(requests.Session, "get", _fake_get)

    client = OpenMeteoClient(_config())
    with pytest.raises(RuntimeError):
        client.fetch_slot_precipitations(
            [datetime(2026, 4, 11, 6, 0, tzinfo=timezone.utc)],
            lat=45.470463,
            lon=4.505748,
        )


def test_fetch_slot_precipitations_raises_when_no_values_for_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_get(
        self: requests.Session,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
        timeout: float,
    ) -> _MockResponse:
        return _MockResponse(
            status_code=200,
            payload={
                "hourly": {
                    "time": ["2026-04-11T06:00"],
                    "precipitation": [None],
                }
            },
        )

    monkeypatch.setattr(requests.Session, "get", _fake_get)

    client = OpenMeteoClient(_config())
    with pytest.raises(RuntimeError):
        client.fetch_slot_precipitations(
            [datetime(2026, 4, 11, 6, 0, tzinfo=timezone.utc)],
            lat=45.470463,
            lon=4.505748,
        )


def test_fetch_slot_precipitations_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_get(
        self: requests.Session,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
        timeout: float,
    ) -> _MockResponse:
        return _MockResponse(status_code=400, payload={"error": True}, text="bad request")

    monkeypatch.setattr(requests.Session, "get", _fake_get)

    client = OpenMeteoClient(_config())
    with pytest.raises(RuntimeError):
        client.fetch_slot_precipitations(
            [datetime(2026, 4, 11, 6, 0, tzinfo=timezone.utc)],
            lat=45.470463,
            lon=4.505748,
        )