"""The booking state machine."""
from __future__ import annotations

from enum import Enum


class BookingState(str, Enum):
    HELD = "held"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    COMPLETED = "completed"


# The only transitions the system will perform. Anything else raises.
TRANSITIONS: dict[BookingState, frozenset[BookingState]] = {
    BookingState.HELD: frozenset({BookingState.CONFIRMED, BookingState.CANCELLED, BookingState.EXPIRED}),
    BookingState.CONFIRMED: frozenset({BookingState.CANCELLED, BookingState.COMPLETED}),
    BookingState.CANCELLED: frozenset(),
    BookingState.EXPIRED: frozenset(),
    BookingState.COMPLETED: frozenset(),
}

# States that still occupy the slot.
ACTIVE_STATES = frozenset({BookingState.HELD, BookingState.CONFIRMED})


class TransitionError(ValueError):
    """An illegal state transition was attempted."""


def can_transition(current: BookingState, target: BookingState) -> bool:
    return target in TRANSITIONS.get(current, frozenset())


def transition(current: BookingState, target: BookingState) -> BookingState:
    if not can_transition(current, target):
        raise TransitionError(f"cannot move a booking from {current.value} to {target.value}")
    return target
