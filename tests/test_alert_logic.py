from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.alert_logic import SlotName, build_idempotency_key, is_rainy, resolve_slot, slot_hours_utc


def test_resolve_slot_morning() -> None:
    timezone_info = ZoneInfo("Europe/Paris")
    now_local = datetime(2026, 4, 11, 7, 15, tzinfo=timezone_info)
    assert resolve_slot(now_local, date(2026, 4, 11)) is SlotName.MORNING


def test_resolve_slot_afternoon() -> None:
    timezone_info = ZoneInfo("Europe/Paris")
    now_local = datetime(2026, 4, 11, 14, 0, tzinfo=timezone_info)
    assert resolve_slot(now_local, date(2026, 4, 11)) is SlotName.AFTERNOON


def test_resolve_slot_out_of_window() -> None:
    timezone_info = ZoneInfo("Europe/Paris")
    now_local = datetime(2026, 4, 11, 19, 0, tzinfo=timezone_info)
    assert resolve_slot(now_local, date(2026, 4, 11)) is None


def test_slot_hours_utc_returns_6_hours_per_slot() -> None:
    timezone_info = ZoneInfo("Europe/Paris")
    target_date = date(2026, 4, 11)
    morning_hours = slot_hours_utc(target_date, SlotName.MORNING, timezone_info)
    afternoon_hours = slot_hours_utc(target_date, SlotName.AFTERNOON, timezone_info)

    assert len(morning_hours) == 6
    assert len(afternoon_hours) == 6
    assert morning_hours[0].astimezone(timezone_info).hour == 6
    assert afternoon_hours[-1].astimezone(timezone_info).hour == 17


def test_is_rainy() -> None:
    assert is_rainy([0.0, 1.0, 0.0])
    assert is_rainy([1.2])
    assert not is_rainy([0.0, 0.99, 0.0])


def test_build_idempotency_key() -> None:
    assert build_idempotency_key(date(2026, 4, 11), SlotName.MORNING) == "meteo-alert/2026-04-11/morning"
