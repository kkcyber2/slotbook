import threading
from datetime import date, datetime

import pytest

from slotbook.engine import BookingEngine, BookingError, SlotTaken
from slotbook.state import BookingState


class Clock:
    def __init__(self, start: float = 1_000_000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now


def make_engine(**kw):
    clock = Clock()
    engine = BookingEngine(clock=clock, **kw)
    engine.add_resource("room-a", "Room A")
    return engine, clock


def test_hold_creates_a_held_booking():
    engine, _ = make_engine()
    booking = engine.hold("room-a", "2026-11-03T10:00", "ada@example.com")
    assert booking.state is BookingState.HELD
    assert booking.expires_at is not None


def test_hold_on_an_unknown_resource_raises():
    engine, _ = make_engine()
    with pytest.raises(BookingError, match="unknown resource"):
        engine.hold("nope", "2026-11-03T10:00", "ada@example.com")


def test_hold_requires_a_customer():
    engine, _ = make_engine()
    with pytest.raises(BookingError, match="customer"):
        engine.hold("room-a", "2026-11-03T10:00", "   ")


def test_double_hold_on_the_same_slot_is_refused():
    engine, _ = make_engine()
    engine.hold("room-a", "2026-11-03T10:00", "ada@example.com")
    with pytest.raises(SlotTaken):
        engine.hold("room-a", "2026-11-03T10:00", "bob@example.com")


def test_the_same_slot_on_another_resource_is_fine():
    engine, _ = make_engine()
    engine.add_resource("room-b", "Room B")
    engine.hold("room-a", "2026-11-03T10:00", "ada@example.com")
    assert engine.hold("room-b", "2026-11-03T10:00", "bob@example.com").state is BookingState.HELD


def test_confirm_moves_to_confirmed_and_clears_the_deadline():
    engine, _ = make_engine()
    booking = engine.hold("room-a", "2026-11-03T10:00", "ada@example.com")
    confirmed = engine.confirm(booking.id)
    assert confirmed.state is BookingState.CONFIRMED
    assert confirmed.expires_at is None


def test_confirming_twice_is_refused():
    engine, _ = make_engine()
    booking = engine.hold("room-a", "2026-11-03T10:00", "ada@example.com")
    engine.confirm(booking.id)
    with pytest.raises(Exception):
        engine.confirm(booking.id)


def test_release_frees_the_slot():
    engine, _ = make_engine()
    booking = engine.hold("room-a", "2026-11-03T10:00", "ada@example.com")
    engine.release(booking.id)
    assert engine.hold("room-a", "2026-11-03T10:00", "bob@example.com").state is BookingState.HELD


def test_an_expired_hold_frees_the_slot():
    engine, clock = make_engine(hold_minutes=10)
    engine.hold("room-a", "2026-11-03T10:00", "ada@example.com")
    clock.now += 11 * 60
    # The sweep runs on the next read, so the slot is available again.
    assert engine.hold("room-a", "2026-11-03T10:00", "bob@example.com").state is BookingState.HELD


def test_an_expired_hold_is_marked_expired():
    engine, clock = make_engine(hold_minutes=10)
    booking = engine.hold("room-a", "2026-11-03T10:00", "ada@example.com")
    clock.now += 11 * 60
    assert engine.get(booking.id).state is BookingState.EXPIRED


def test_a_confirmed_booking_does_not_expire():
    engine, clock = make_engine(hold_minutes=10)
    booking = engine.hold("room-a", "2026-11-03T10:00", "ada@example.com")
    engine.confirm(booking.id)
    clock.now += 60 * 60
    assert engine.get(booking.id).state is BookingState.CONFIRMED


def test_availability_marks_taken_slots():
    engine, _ = make_engine()
    engine.hold("room-a", "2026-11-03T10:00", "ada@example.com")
    slots = {s["slot"]: s["available"] for s in engine.availability("room-a", date(2026, 11, 3))}
    assert slots["2026-11-03T10:00"] is False
    assert slots["2026-11-03T11:00"] is True


def test_concurrent_holds_on_one_slot_produce_exactly_one_winner():
    engine, _ = make_engine()
    winners: list[str] = []
    losers: list[str] = []
    barrier = threading.Barrier(12)

    def attempt(index: int) -> None:
        barrier.wait()
        try:
            booking = engine.hold("room-a", "2026-11-03T10:00", f"user{index}@example.com")
            winners.append(booking.id)
        except SlotTaken:
            losers.append(f"user{index}")

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(winners) == 1
    assert len(losers) == 11


def test_history_records_every_transition():
    engine, _ = make_engine()
    booking = engine.hold("room-a", "2026-11-03T10:00", "ada@example.com")
    engine.confirm(booking.id)
    states = [state for state, _ in booking.history]
    assert states == ["held", "confirmed"]


def test_bookings_can_be_filtered_by_state():
    engine, _ = make_engine()
    first = engine.hold("room-a", "2026-11-03T10:00", "ada@example.com")
    engine.hold("room-a", "2026-11-03T11:00", "bob@example.com")
    engine.confirm(first.id)
    assert len(engine.bookings(state=BookingState.CONFIRMED)) == 1
    assert len(engine.bookings(state=BookingState.HELD)) == 1


def test_public_dict_is_serialisable():
    import json

    engine, _ = make_engine()
    booking = engine.hold("room-a", "2026-11-03T10:00", "ada@example.com")
    json.dumps(booking.public())
