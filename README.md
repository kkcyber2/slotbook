# Slotbook

A booking engine with the parts that are actually hard: **holds that expire**,
**double-booking prevention under concurrency**, and a **state machine** that refuses
illegal transitions.

## The three hard problems

**1. Two people booking the same slot.** The naive check-then-write has a race: both
requests read "free", both write. Slotbook takes a lock around the check *and* the
write, and the test suite proves it with concurrent threads.

**2. Abandoned carts.** A hold that never expires blocks a slot forever. Holds carry a
deadline and are swept lazily on every read, so no background job is required.

**3. Bookings that change state illegally.** A cancelled booking must not become
confirmed. Transitions are declared in one table and anything not in it raises.

## Quick start

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
uvicorn slotbook.app:app --reload
```

## Try it

```bash
# see availability for a resource on a date
curl -s "localhost:8000/resources/room-a/availability?date=2026-11-03"

# hold a slot for 10 minutes
curl -s localhost:8000/holds -H 'content-type: application/json' \
  -d '{"resource_id":"room-a","slot":"2026-11-03T10:00","customer":"ada@example.com"}'

# confirm it
curl -s localhost:8000/holds/<hold_id>/confirm
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/resources` | list resources |
| `GET` | `/resources/{id}/availability?date=` | free slots for a day |
| `POST` | `/holds` | place a hold |
| `POST` | `/holds/{id}/confirm` | turn a hold into a booking |
| `POST` | `/holds/{id}/release` | give the slot back |
| `POST` | `/bookings/{id}/cancel` | cancel a booking |
| `GET` | `/bookings` | list bookings |

## Tests

```bash
pytest -q
```

## License

MIT — see [LICENSE](LICENSE).

Built by **Konain Sultan Khan (KK)** · <kkdev9715@gmail.com>
[https://github.com/kkcyber2](https://github.com/kkcyber2) · LinkedIn: _add profile URL_
