from datetime import date, datetime

import pytest

from slotbook.slots import day_slots, is_past, parse_date, parse_slot, slot_key


def test_day_slots_covers_the_working_day():
    slots = day_slots(date(2026, 11, 3))
    assert len(slots) == 8
    assert slots[0] == datetime(2026, 11, 3, 9, 0)
    assert slots[-1] == datetime(2026, 11, 3, 16, 0)


def test_day_slots_respects_a_custom_grid():
    slots = day_slots(date(2026, 11, 3), minutes=30)
    assert len(slots) == 16


def test_day_slots_never_overruns_closing_time():
    slots = day_slots(date(2026, 11, 3), minutes=90)
    assert all(s.hour < 17 for s in slots)


def test_invalid_grid_is_rejected():
    with pytest.raises(ValueError):
        day_slots(date(2026, 11, 3), minutes=0)
    with pytest.raises(ValueError):
        day_slots(date(2026, 11, 3), opens=datetime(2026, 1, 1, 17).time(),
                  closes=datetime(2026, 1, 1, 9).time())


def test_parse_date_accepts_iso():
    assert parse_date("2026-11-03") == date(2026, 11, 3)


def test_parse_date_rejects_garbage():
    with pytest.raises(ValueError, match="ISO date"):
        parse_date("03/11/2026")


def test_parse_slot_accepts_iso_minutes():
    assert parse_slot("2026-11-03T10:00") == datetime(2026, 11, 3, 10, 0)


def test_parse_slot_rejects_garbage():
    with pytest.raises(ValueError, match="slot"):
        parse_slot("tomorrow")


def test_slot_key_is_canonical():
    assert slot_key(datetime(2026, 11, 3, 10, 0)) == "2026-11-03T10:00"


def test_is_past():
    now = datetime(2026, 11, 3, 12, 0)
    assert is_past(datetime(2026, 11, 3, 11, 0), now=now) is True
    assert is_past(datetime(2026, 11, 3, 13, 0), now=now) is False
