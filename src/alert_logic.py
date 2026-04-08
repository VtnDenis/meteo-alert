from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from zoneinfo import ZoneInfo
from typing import Sequence


class SlotName(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"


@dataclass(frozen=True, slots=True)
class SlotWindow:
    name: SlotName
    start_hour_inclusive: int
    end_hour_inclusive: int


MORNING_WINDOW = SlotWindow(name=SlotName.MORNING, start_hour_inclusive=6, end_hour_inclusive=11)
AFTERNOON_WINDOW = SlotWindow(name=SlotName.AFTERNOON, start_hour_inclusive=12, end_hour_inclusive=17)
MIN_PRECIPITATION_THRESHOLD_MM = 1.0


def resolve_slot(now_local: datetime, target_date: date) -> SlotName | None:
    if now_local.date() != target_date:
        return None

    hour = now_local.hour
    if MORNING_WINDOW.start_hour_inclusive <= hour <= MORNING_WINDOW.end_hour_inclusive:
        return SlotName.MORNING
    if AFTERNOON_WINDOW.start_hour_inclusive <= hour <= AFTERNOON_WINDOW.end_hour_inclusive:
        return SlotName.AFTERNOON
    return None


def slot_hours_local(target_date: date, slot: SlotName, timezone_info: ZoneInfo) -> list[datetime]:
    window = _window_for_slot(slot)
    return [
        datetime(
            year=target_date.year,
            month=target_date.month,
            day=target_date.day,
            hour=hour,
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=timezone_info,
        )
        for hour in range(window.start_hour_inclusive, window.end_hour_inclusive + 1)
    ]


def slot_hours_utc(target_date: date, slot: SlotName, timezone_info: ZoneInfo) -> list[datetime]:
    return [hour_local.astimezone(timezone.utc) for hour_local in slot_hours_local(target_date, slot, timezone_info)]


def is_rainy(
    precipitation_mm: Sequence[float],
    threshold_mm: float = MIN_PRECIPITATION_THRESHOLD_MM,
) -> bool:
    if threshold_mm < 0:
        raise ValueError("threshold_mm must be >= 0.")
    return any(value >= threshold_mm for value in precipitation_mm)


def build_idempotency_key(target_date: date, slot: SlotName) -> str:
    return f"meteo-alert/{target_date.isoformat()}/{slot.value}"


def slot_label_fr(slot: SlotName) -> str:
    if slot is SlotName.MORNING:
        return "matin"
    return "après-midi"


def _window_for_slot(slot: SlotName) -> SlotWindow:
    if slot is SlotName.MORNING:
        return MORNING_WINDOW
    return AFTERNOON_WINDOW
