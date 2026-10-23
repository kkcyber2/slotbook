"""Slot arithmetic: turning a date and a grid into concrete bookable times."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

DEFAULT_OPEN = time(9, 0)
DEFAULT_CLOSE = time(17, 0)
DEFAULT_MINUTES = 60


def parse_date(value: str) -> date:
    """Parse an ISO date, raising ValueError with a helpful message."""
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"expected an ISO date like 2026-11-03, got {value!r}") from exc


def parse_slot(value: str) -> datetime:
    """Parse an ISO minute-precision slot like 2026-11-03T10:00."""
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"expected a slot like 2026-11-03T10:00, got {value!r}") from exc


def day_slots(
    day: date,
    *,
    opens: time = DEFAULT_OPEN,
    closes: time = DEFAULT_CLOSE,
    minutes: int = DEFAULT_MINUTES,
) -> list[datetime]:
    """Every slot start on `day` between opening and closing time."""
    if minutes <= 0:
        raise ValueError("slot length must be positive")
    if closes <= opens:
        raise ValueError("closing time must be after opening time")
    slots: list[datetime] = []
    cursor = datetime.combine(day, opens)
    end = datetime.combine(day, closes)
    while cursor + timedelta(minutes=minutes) <= end:
        slots.append(cursor)
        cursor += timedelta(minutes=minutes)
    return slots


def slot_key(moment: datetime) -> str:
    """Canonical string form of a slot, used as the storage key."""
    return moment.strftime("%Y-%m-%dT%H:%M")


def is_past(moment: datetime, *, now: datetime | None = None) -> bool:
    return moment < (now or datetime.now())
