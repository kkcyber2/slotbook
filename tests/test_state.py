import pytest

from slotbook.state import (
    ACTIVE_STATES,
    BookingState,
    TransitionError,
    can_transition,
    transition,
)


def test_held_can_be_confirmed():
    assert can_transition(BookingState.HELD, BookingState.CONFIRMED) is True


def test_held_can_expire_or_be_cancelled():
    assert can_transition(BookingState.HELD, BookingState.EXPIRED) is True
    assert can_transition(BookingState.HELD, BookingState.CANCELLED) is True


def test_confirmed_cannot_go_back_to_held():
    assert can_transition(BookingState.CONFIRMED, BookingState.HELD) is False


def test_cancelled_is_terminal():
    for target in BookingState:
        assert can_transition(BookingState.CANCELLED, target) is False


def test_expired_is_terminal():
    for target in BookingState:
        assert can_transition(BookingState.EXPIRED, target) is False


def test_completed_is_terminal():
    for target in BookingState:
        assert can_transition(BookingState.COMPLETED, target) is False


def test_transition_returns_the_target():
    assert transition(BookingState.HELD, BookingState.CONFIRMED) is BookingState.CONFIRMED


def test_illegal_transition_raises():
    with pytest.raises(TransitionError, match="cannot move"):
        transition(BookingState.CANCELLED, BookingState.CONFIRMED)


def test_active_states_are_held_and_confirmed():
    assert ACTIVE_STATES == {BookingState.HELD, BookingState.CONFIRMED}
