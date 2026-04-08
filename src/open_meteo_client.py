from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Sequence

import requests

from src.config import AppConfig


@dataclass(frozen=True, slots=True)
class ForecastPoint:
    forecast_time_utc: datetime
    precipitation_mm: float
    coverage_id: str
    run_time_utc: datetime


class OpenMeteoClient:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._session = requests.Session()

    def fetch_slot_precipitations(
        self,
        slot_hours_utc: Sequence[datetime],
        lat: float,
        lon: float,
    ) -> list[ForecastPoint]:
        normalized_hours = [_ensure_utc(value) for value in slot_hours_utc]
        if not normalized_hours:
            return []

        requested_hours = list(dict.fromkeys(normalized_hours))
        requested_hours_sorted = sorted(requested_hours)

        run_time_utc = datetime.now(timezone.utc)
        coverage_id = f"open-meteo:{self._config.open_meteo_model}"

        response_data = self._fetch_precipitation_payload(
            lat=lat,
            lon=lon,
            start_hour_utc=requested_hours_sorted[0],
            end_hour_utc=requested_hours_sorted[-1],
        )
        precipitation_by_hour = _extract_precipitation_by_hour(response_data)

        points: list[ForecastPoint] = []
        for hour_utc in requested_hours:
            precipitation_mm = precipitation_by_hour.get(hour_utc)
            if precipitation_mm is None:
                continue
            points.append(
                ForecastPoint(
                    forecast_time_utc=hour_utc,
                    precipitation_mm=precipitation_mm,
                    coverage_id=coverage_id,
                    run_time_utc=run_time_utc,
                )
            )

        if points:
            return points

        raise RuntimeError("No precipitation values could be retrieved for the requested slot.")

    def _fetch_precipitation_payload(
        self,
        lat: float,
        lon: float,
        start_hour_utc: datetime,
        end_hour_utc: datetime,
    ) -> dict[str, Any]:
        start_hour = start_hour_utc.strftime("%Y-%m-%dT%H:%M")
        end_hour = (end_hour_utc + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
        params = {
            "latitude": f"{lat:.6f}",
            "longitude": f"{lon:.6f}",
            "hourly": "precipitation",
            "timezone": "GMT",
            "start_hour": start_hour,
            "end_hour": end_hour,
            "models": self._config.open_meteo_model,
            "precipitation_unit": "mm",
        }

        response = self._session.get(
            self._config.open_meteo_base_url,
            params=params,
            headers={"accept": "application/json"},
            timeout=self._config.open_meteo_timeout_seconds,
        )
        _raise_for_status(response, "Open-Meteo forecast request failed")

        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError("Open-Meteo response is not valid JSON.") from exc

        if not isinstance(payload, dict):
            raise RuntimeError("Open-Meteo response payload must be a JSON object.")
        return payload


def _extract_precipitation_by_hour(payload: dict[str, Any]) -> dict[datetime, float]:
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise RuntimeError("Open-Meteo response does not include an 'hourly' object.")

    raw_times = hourly.get("time")
    raw_precipitations = hourly.get("precipitation")
    if not isinstance(raw_times, list):
        raise RuntimeError("Open-Meteo response hourly.time must be an array.")
    if not isinstance(raw_precipitations, list):
        raise RuntimeError("Open-Meteo response hourly.precipitation must be an array.")
    if len(raw_times) != len(raw_precipitations):
        raise RuntimeError("Open-Meteo response hourly.time and hourly.precipitation lengths differ.")

    precipitation_by_hour: dict[datetime, float] = {}
    for raw_time, raw_precipitation in zip(raw_times, raw_precipitations):
        if not isinstance(raw_time, str):
            raise RuntimeError("Open-Meteo response hourly.time entries must be strings.")

        forecast_time_utc = _parse_open_meteo_time_utc(raw_time)
        if raw_precipitation is None:
            continue
        if isinstance(raw_precipitation, bool) or not isinstance(raw_precipitation, (int, float)):
            raise RuntimeError("Open-Meteo response hourly.precipitation entries must be numeric or null.")

        precipitation_by_hour[forecast_time_utc] = max(0.0, float(raw_precipitation))

    return precipitation_by_hour


def _parse_open_meteo_time_utc(raw_time: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(raw_time)
    except ValueError as exc:
        raise RuntimeError(f"Invalid Open-Meteo hourly time value: {raw_time}") from exc

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Datetime must be timezone-aware (UTC).")
    return value.astimezone(timezone.utc)


def _raise_for_status(response: requests.Response, context: str) -> None:
    if response.status_code < 400:
        return

    body_preview = response.text.strip().replace("\n", " ")[:300]
    raise RuntimeError(f"{context}: HTTP {response.status_code} - {body_preview}")