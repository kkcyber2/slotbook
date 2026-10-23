def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_resources_are_listed(client):
    ids = {r["id"] for r in client.get("/resources").json()}
    assert "room-a" in ids


def test_availability_returns_the_day_grid(client):
    slots = client.get("/resources/room-a/availability?date=2026-11-03").json()
    assert len(slots) == 8
    assert all("available" in s for s in slots)


def test_availability_for_an_unknown_resource_is_404(client):
    assert client.get("/resources/nope/availability?date=2026-11-03").status_code == 404


def test_availability_with_a_bad_date_is_422(client):
    assert client.get("/resources/room-a/availability?date=03/11/2026").status_code == 422


def test_hold_then_confirm(client):
    hold = client.post(
        "/holds",
        json={"resource_id": "room-a", "slot": "2026-11-03T10:00", "customer": "ada@example.com"},
    )
    assert hold.status_code == 201
    booking_id = hold.json()["id"]
    confirmed = client.post(f"/holds/{booking_id}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["state"] == "confirmed"


def test_second_hold_on_the_same_slot_is_409(client):
    payload = {"resource_id": "room-a", "slot": "2026-11-03T10:00", "customer": "ada@example.com"}
    assert client.post("/holds", json=payload).status_code == 201
    payload["customer"] = "bob@example.com"
    assert client.post("/holds", json=payload).status_code == 409


def test_release_frees_the_slot(client):
    payload = {"resource_id": "room-a", "slot": "2026-11-03T10:00", "customer": "ada@example.com"}
    booking_id = client.post("/holds", json=payload).json()["id"]
    assert client.post(f"/holds/{booking_id}/release").status_code == 200
    payload["customer"] = "bob@example.com"
    assert client.post("/holds", json=payload).status_code == 201


def test_confirming_an_unknown_hold_is_404(client):
    assert client.post("/holds/bk_nope/confirm").status_code == 404


def test_confirming_a_released_hold_is_409(client):
    payload = {"resource_id": "room-a", "slot": "2026-11-03T10:00", "customer": "ada@example.com"}
    booking_id = client.post("/holds", json=payload).json()["id"]
    client.post(f"/holds/{booking_id}/release")
    assert client.post(f"/holds/{booking_id}/confirm").status_code == 409


def test_unknown_state_filter_is_422(client):
    assert client.get("/bookings?state=bogus").status_code == 422


def test_bookings_are_listed(client):
    client.post(
        "/holds",
        json={"resource_id": "room-a", "slot": "2026-11-03T10:00", "customer": "ada@example.com"},
    )
    assert len(client.get("/bookings").json()) == 1
