"""HTTP surface for the booking engine."""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from .engine import BookingEngine, BookingError, SlotTaken
from .slots import parse_date
from .state import BookingState, TransitionError

engine = BookingEngine()
engine.add_resource("room-a", "Meeting Room A")
engine.add_resource("room-b", "Meeting Room B")
engine.add_resource("studio", "Recording Studio")

app = FastAPI(title="Slotbook", version="1.0.0", description="Booking engine with expiring holds.")


class HoldRequest(BaseModel):
    resource_id: str
    slot: str = Field(description="ISO minute slot, e.g. 2026-11-03T10:00")
    customer: str = Field(min_length=1, max_length=200)


@app.get("/health", tags=["meta"])
def health() -> dict[str, Any]:
    return {"status": "ok", "bookings": len(engine.bookings())}


@app.get("/resources", tags=["resources"])
def resources() -> list[dict[str, Any]]:
    return engine.resources()


@app.get("/resources/{resource_id}/availability", tags=["resources"])
def availability(resource_id: str, date: str) -> list[dict[str, Any]]:
    if engine.get_resource(resource_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "resource not found")
    try:
        day = parse_date(date)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return engine.availability(resource_id, day)


@app.post("/holds", status_code=201, tags=["bookings"])
def create_hold(body: HoldRequest) -> dict[str, Any]:
    try:
        return engine.hold(body.resource_id, body.slot, body.customer).public()
    except SlotTaken as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except BookingError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@app.post("/holds/{booking_id}/confirm", tags=["bookings"])
def confirm(booking_id: str) -> dict[str, Any]:
    try:
        return engine.confirm(booking_id).public()
    except BookingError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except TransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@app.post("/holds/{booking_id}/release", tags=["bookings"])
def release(booking_id: str) -> dict[str, Any]:
    try:
        return engine.release(booking_id).public()
    except BookingError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except TransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@app.post("/bookings/{booking_id}/cancel", tags=["bookings"])
def cancel(booking_id: str) -> dict[str, Any]:
    return release(booking_id)


@app.get("/bookings", tags=["bookings"])
def list_bookings(state: str | None = None) -> list[dict[str, Any]]:
    parsed = None
    if state is not None:
        try:
            parsed = BookingState(state)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"unknown state {state!r}") from exc
    return [b.public() for b in engine.bookings(state=parsed)]
