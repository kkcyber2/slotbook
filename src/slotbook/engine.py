"""The booking engine: holds, confirmations and concurrency-safe slot allocation."""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from .slots import day_slots, is_past, parse_slot, slot_key
from .state import ACTIVE_STATES, BookingState, TransitionError, transition

DEFAULT_HOLD_MINUTES = 10


@dataclass
class Booking:
    id: str
    resource_id: str
    slot: datetime
    customer: str
    state: BookingState = BookingState.HELD
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    history: list[tuple[str, float]] = field(default_factory=list)

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "resource_id": self.resource_id,
            "slot": slot_key(self.slot),
            "customer": self.customer,
            "state": self.state.value,
            "expires_at": self.expires_at,
            "history": [{"state": s, "at": t} for s, t in self.history],
        }


class BookingError(ValueError):
    """A booking request could not be satisfied."""


class SlotTaken(BookingError):
    """The slot is already held or booked."""


class BookingEngine:
    """In-memory booking engine.

    A single re-entrant lock guards the check-and-write, which is what makes
    concurrent holds on the same slot safe. A real deployment would use a database
    unique constraint; the invariant is the same.
    """

    def __init__(self, *, hold_minutes: int = DEFAULT_HOLD_MINUTES, clock=time.time) -> None:
        self._lock = threading.RLock()
        self._bookings: dict[str, Booking] = {}
        self._by_slot: dict[tuple[str, str], str] = {}
        self._resources: dict[str, dict[str, Any]] = {}
        self.hold_minutes = hold_minutes
        self._clock = clock

    # -- resources ---------------------------------------------------------
    def add_resource(self, resource_id: str, name: str, *, capacity: int = 1) -> dict[str, Any]:
        with self._lock:
            resource = {"id": resource_id, "name": name, "capacity": capacity}
            self._resources[resource_id] = resource
            return resource

    def resources(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._resources.values())

    def get_resource(self, resource_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._resources.get(resource_id)

    # -- expiry ------------------------------------------------------------
    def _sweep(self) -> None:
        """Expire any hold whose deadline has passed. Called on every read."""
        now = self._clock()
        for booking in list(self._bookings.values()):
            if (
                booking.state is BookingState.HELD
                and booking.expires_at is not None
                and booking.expires_at <= now
            ):
                booking.state = transition(booking.state, BookingState.EXPIRED)
                booking.history.append((BookingState.EXPIRED.value, now))
                self._by_slot.pop((booking.resource_id, slot_key(booking.slot)), None)

    # -- availability ------------------------------------------------------
    def availability(self, resource_id: str, day: date) -> list[dict[str, Any]]:
        with self._lock:
            self._sweep()
            taken = {
                slot_key(b.slot)
                for b in self._bookings.values()
                if b.resource_id == resource_id and b.state in ACTIVE_STATES
            }
            now = datetime.fromtimestamp(self._clock())
            out = []
            for moment in day_slots(day):
                key = slot_key(moment)
                out.append(
                    {
                        "slot": key,
                        "available": key not in taken and not is_past(moment, now=now),
                    }
                )
            return out

    # -- holds -------------------------------------------------------------
    def hold(self, resource_id: str, slot: str, customer: str) -> Booking:
        moment = parse_slot(slot)
        with self._lock:
            if resource_id not in self._resources:
                raise BookingError(f"unknown resource {resource_id!r}")
            if not customer.strip():
                raise BookingError("a customer is required")
            self._sweep()
            key = (resource_id, slot_key(moment))
            if key in self._by_slot:
                raise SlotTaken(f"{slot_key(moment)} is already taken for {resource_id}")
            now = self._clock()
            booking = Booking(
                id=f"bk_{uuid.uuid4().hex[:10]}",
                resource_id=resource_id,
                slot=moment,
                customer=customer.strip(),
                state=BookingState.HELD,
                created_at=now,
                expires_at=now + self.hold_minutes * 60,
            )
            booking.history.append((BookingState.HELD.value, now))
            self._bookings[booking.id] = booking
            self._by_slot[key] = booking.id
            return booking

    def get(self, booking_id: str) -> Booking | None:
        with self._lock:
            self._sweep()
            return self._bookings.get(booking_id)

    def confirm(self, booking_id: str) -> Booking:
        with self._lock:
            self._sweep()
            booking = self._bookings.get(booking_id)
            if booking is None:
                raise BookingError("booking not found")
            booking.state = transition(booking.state, BookingState.CONFIRMED)
            booking.expires_at = None
            booking.history.append((BookingState.CONFIRMED.value, self._clock()))
            return booking

    def release(self, booking_id: str) -> Booking:
        with self._lock:
            booking = self._bookings.get(booking_id)
            if booking is None:
                raise BookingError("booking not found")
            booking.state = transition(booking.state, BookingState.CANCELLED)
            booking.expires_at = None
            booking.history.append((BookingState.CANCELLED.value, self._clock()))
            self._by_slot.pop((booking.resource_id, slot_key(booking.slot)), None)
            return booking

    def cancel(self, booking_id: str) -> Booking:
        return self.release(booking_id)

    def complete(self, booking_id: str) -> Booking:
        with self._lock:
            booking = self._bookings.get(booking_id)
            if booking is None:
                raise BookingError("booking not found")
            booking.state = transition(booking.state, BookingState.COMPLETED)
            booking.history.append((BookingState.COMPLETED.value, self._clock()))
            return booking

    def bookings(self, *, state: BookingState | None = None) -> list[Booking]:
        with self._lock:
            self._sweep()
            rows = list(self._bookings.values())
        if state is not None:
            rows = [b for b in rows if b.state is state]
        return sorted(rows, key=lambda b: b.slot)

    def clear(self) -> None:
        with self._lock:
            self._bookings.clear()
            self._by_slot.clear()
            self._resources.clear()
