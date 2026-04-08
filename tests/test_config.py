from __future__ import annotations

from datetime import date

import pytest

from src.config import AppConfig, DEFAULT_OPEN_METEO_BASE_URL


def _base_env() -> dict[str, str]:
    return {
        "OPEN_METEO_MODEL": "best_match",
        "RESEND_API_KEY": "dummy",
        "RESEND_FROM": "alerts@example.com",
        "WHATSAPP_ACCESS_TOKEN": "token_123",
        "WHATSAPP_PHONE_NUMBER_ID": "1906385232743451",
        "WHATSAPP_BUSINESS_ACCOUNT_ID": "104996122399160",
    }


def test_from_mapping_valid_minimal() -> None:
    config = AppConfig.from_mapping(_base_env())
    assert config.open_meteo_model == "best_match"
    assert config.target_date == date(2026, 4, 11)
    assert config.open_meteo_base_url == DEFAULT_OPEN_METEO_BASE_URL


def test_from_mapping_normalizes_open_meteo_model_auto() -> None:
    env = _base_env()
    env["OPEN_METEO_MODEL"] = "auto"

    config = AppConfig.from_mapping(env)

    assert config.open_meteo_model == "best_match"


def test_from_mapping_fails_with_invalid_open_meteo_url() -> None:
    env = _base_env()
    env["OPEN_METEO_BASE_URL"] = "http://api.open-meteo.com/v1/forecast"
    with pytest.raises(ValueError):
        AppConfig.from_mapping(env)


def test_from_mapping_fails_with_invalid_coordinates() -> None:
    env = _base_env()
    env["TARGET_LAT"] = "200"
    with pytest.raises(ValueError):
        AppConfig.from_mapping(env)


def test_from_mapping_fails_with_invalid_whatsapp_recipient() -> None:
    env = _base_env()
    env["WHATSAPP_RECIPIENT_NUMBER"] = "0624018317"
    with pytest.raises(ValueError):
        AppConfig.from_mapping(env)
