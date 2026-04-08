from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
from typing import Mapping

DEFAULT_OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_OPEN_METEO_MODEL = "auto"
DEFAULT_TARGET_DATE = "2026-04-11"
DEFAULT_TARGET_TIMEZONE = "Europe/Paris"
DEFAULT_TARGET_LAT = "45.470463"
DEFAULT_TARGET_LON = "4.505748"
DEFAULT_ALERT_EMAIL_TO = "vtndenis@gmail.com"
DEFAULT_OPEN_METEO_TIMEOUT_SECONDS = "30"


@dataclass(frozen=True, slots=True)
class AppConfig:
    open_meteo_base_url: str
    open_meteo_model: str
    open_meteo_timeout_seconds: float

    resend_api_key: str
    resend_from: str
    resend_to: str

    target_date: date
    timezone_name: str
    target_lat: float
    target_lon: float

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls.from_mapping(dict(os.environ))

    @classmethod
    def from_mapping(cls, env: Mapping[str, str]) -> "AppConfig":
        errors: list[str] = []

        open_meteo_base_url = _none_if_blank(env.get("OPEN_METEO_BASE_URL")) or DEFAULT_OPEN_METEO_BASE_URL
        if not open_meteo_base_url.startswith("https://"):
            errors.append("OPEN_METEO_BASE_URL must start with https://")

        open_meteo_model = _none_if_blank(env.get("OPEN_METEO_MODEL")) or DEFAULT_OPEN_METEO_MODEL

        open_meteo_timeout_seconds = _parse_float(
            name="OPEN_METEO_TIMEOUT_SECONDS",
            raw=env.get("OPEN_METEO_TIMEOUT_SECONDS", DEFAULT_OPEN_METEO_TIMEOUT_SECONDS),
            errors=errors,
        )
        if open_meteo_timeout_seconds <= 0:
            errors.append("OPEN_METEO_TIMEOUT_SECONDS must be > 0.")

        resend_api_key = _require_non_blank(env, "RESEND_API_KEY", errors)
        resend_from = _require_non_blank(env, "RESEND_FROM", errors)
        resend_to = (env.get("ALERT_EMAIL_TO") or DEFAULT_ALERT_EMAIL_TO).strip()

        if resend_from and not _looks_like_email(resend_from):
            errors.append("RESEND_FROM must be a valid email address.")
        if resend_to and not _looks_like_email(resend_to):
            errors.append("ALERT_EMAIL_TO must be a valid email address.")

        target_date = _parse_date(
            name="TARGET_DATE",
            raw=env.get("TARGET_DATE", DEFAULT_TARGET_DATE),
            errors=errors,
        )
        timezone_name = (env.get("TARGET_TIMEZONE") or DEFAULT_TARGET_TIMEZONE).strip()
        if not timezone_name:
            errors.append("TARGET_TIMEZONE cannot be blank.")

        target_lat = _parse_float(
            name="TARGET_LAT",
            raw=env.get("TARGET_LAT", DEFAULT_TARGET_LAT),
            errors=errors,
        )
        target_lon = _parse_float(
            name="TARGET_LON",
            raw=env.get("TARGET_LON", DEFAULT_TARGET_LON),
            errors=errors,
        )
        if not (-90 <= target_lat <= 90):
            errors.append("TARGET_LAT must be between -90 and 90.")
        if not (-180 <= target_lon <= 180):
            errors.append("TARGET_LON must be between -180 and 180.")

        if errors:
            raise ValueError("Invalid configuration:\n- " + "\n- ".join(errors))

        return cls(
            open_meteo_base_url=open_meteo_base_url,
            open_meteo_model=open_meteo_model,
            open_meteo_timeout_seconds=open_meteo_timeout_seconds,
            resend_api_key=resend_api_key,
            resend_from=resend_from,
            resend_to=resend_to,
            target_date=target_date,
            timezone_name=timezone_name,
            target_lat=target_lat,
            target_lon=target_lon,
        )

    def safe_for_logs(self) -> dict[str, object]:
        return {
            "open_meteo_base_url": self.open_meteo_base_url,
            "open_meteo_model": self.open_meteo_model,
            "open_meteo_timeout_seconds": self.open_meteo_timeout_seconds,
            "resend_from": self.resend_from,
            "resend_to": self.resend_to,
            "target_date": self.target_date.isoformat(),
            "timezone_name": self.timezone_name,
            "target_lat": self.target_lat,
            "target_lon": self.target_lon,
        }


def _none_if_blank(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _require_non_blank(env: Mapping[str, str], key: str, errors: list[str]) -> str:
    value = _none_if_blank(env.get(key))
    if value is None:
        errors.append(f"{key} is required.")
        return ""
    return value


def _parse_float(name: str, raw: str | None, errors: list[str]) -> float:
    if raw is None:
        errors.append(f"{name} is required.")
        return 0.0
    try:
        return float(raw)
    except ValueError:
        errors.append(f"{name} must be a valid float.")
        return 0.0


def _parse_date(name: str, raw: str | None, errors: list[str]) -> date:
    if raw is None or not raw.strip():
        errors.append(f"{name} is required.")
        return date.today()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        errors.append(f"{name} must be in YYYY-MM-DD format.")
        return date.today()


def _looks_like_email(value: str) -> bool:
    local, separator, domain = value.partition("@")
    if not separator:
        return False
    if not local:
        return False
    if "." not in domain:
        return False
    if domain.startswith(".") or domain.endswith("."):
        return False
    return True
