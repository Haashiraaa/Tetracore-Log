# tests/api/routes/test_truck_queue.py
"""A truck's visit: Queued -> On site -> Departed, or Queued -> Left queue."""

import base64
import uuid
from datetime import timedelta

from backend.src.api import event_service
from backend.src.config.settings import Settings
from backend.src.db.orm.tables import DutyEntry, TruckEntry
from backend.src.db.session import create_session
from backend.src.security.tokens import utcnow
from tests._helpers import make_actor

PNG_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64).decode()


def register(client, who, **over):
    body = {"id": str(uuid.uuid4()), "plate_number": "abc-123 xy",
            "driver_name": "Musa Ibrahim", "driver_phone": "08030000000", **over}
    return client.post("/api/trucks/entries", json=body, headers=who.headers)


def enter(client, who, entry_id, signature: str | None = PNG_B64):
    body = {} if signature is None else {"signature": signature}
    return client.post(f"/api/trucks/entries/{entry_id}/enter", json=body, headers=who.headers)


def leave(client, who, entry_id, reason="No CNG left"):
    return client.post(f"/api/trucks/entries/{entry_id}/leave-queue",
                       json={"reason": reason}, headers=who.headers)


def out(client, who, entry_id):
    return client.post(f"/api/trucks/entries/{entry_id}/sign-out",
                       json={"signature": PNG_B64}, headers=who.headers)


def feed_kinds(client, admin):
    return [e["kind"] for e in reversed(
        client.get("/api/admin/events", headers=admin.headers).json())]


def test_a_new_truck_joins_the_queue_without_a_signature(client, officer_a):
    r = register(client, officer_a)
    assert r.status_code == 201, r.text
    e = r.json()
    assert e["status"] == "queued" and e["queued_gate"] == 1
    assert e["entered_at"] is None and e["has_signature"] is False
    assert e["gate_in"] is None and e["signed_out_at"] is None


def test_enter_now_needs_the_signature(client, officer_a):
    assert register(client, officer_a, enter_now=True).status_code == 422
    r = register(client, officer_a, enter_now=True, signature=PNG_B64)
    e = r.json()
    assert r.status_code == 201 and e["status"] == "on_site"
    assert e["entered_at"] is not None and e["gate_in"] == 1 and e["has_signature"] is True


def test_queued_then_let_in_then_out(client, officer_a, admin):
    qd = register(client, officer_a).json()
    assert enter(client, officer_a, qd["id"], signature="").status_code == 422
    let_in = enter(client, officer_a, qd["id"])
    assert let_in.status_code == 200, let_in.text
    e = let_in.json()
    assert e["status"] == "on_site" and e["gate_in"] == 1 and e["has_signature"] is True
    assert e["entered_by"] == str(officer_a.id) and e["entered_at"] is not None
    assert e["signed_in_at"] == qd["signed_in_at"]  # the queue time is kept
    gone = out(client, officer_a, qd["id"])
    assert gone.status_code == 200
    assert gone.json()["status"] == "departed" and gone.json()["gate_out"] == 1
    assert feed_kinds(client, admin) == ["truck_queued", "truck_in", "truck_out"]


def test_entering_twice_replays_quietly(client, officer_a, admin):
    qd = register(client, officer_a).json()
    first = enter(client, officer_a, qd["id"]).json()
    again = enter(client, officer_a, qd["id"])
    assert again.status_code == 200 and again.json()["entered_at"] == first["entered_at"]
    assert feed_kinds(client, admin) == ["truck_queued", "truck_in"]


def test_a_queued_truck_cannot_sign_out(client, officer_a):
    qd = register(client, officer_a).json()
    r = out(client, officer_a, qd["id"])
    assert r.status_code == 409 and r.json()["detail"]["code"] == "invalid_truck_state"
    assert client.get("/api/trucks/entries", headers=officer_a.headers).json()[0][
        "status"] == "queued"


def test_a_truck_that_gave_up_leaves_the_queue_with_a_reason(client, officer_a, admin):
    qd = register(client, officer_a).json()
    assert leave(client, officer_a, qd["id"], reason="").status_code == 422
    r = leave(client, officer_a, qd["id"], reason="  Ran out of patience, no CNG  ")
    assert r.status_code == 200, r.text
    e = r.json()
    assert e["status"] == "left_queue"
    assert e["left_queue_reason"] == "Ran out of patience, no CNG"
    assert e["signed_out_at"] is not None and e["signed_out_by"] == str(officer_a.id)
    assert enter(client, officer_a, qd["id"]).json()["status"] == "left_queue"  # too late
    assert feed_kinds(client, admin) == ["truck_queued", "truck_left_queue"]
    # it is no longer open, so the same plate can queue again
    assert register(client, officer_a).status_code == 201


def test_a_truck_that_is_inside_cannot_leave_the_queue(client, officer_a):
    e = register(client, officer_a, enter_now=True, signature=PNG_B64).json()
    r = leave(client, officer_a, e["id"])
    assert r.status_code == 409 and r.json()["detail"]["code"] == "invalid_truck_state"


def test_a_truck_is_queued_or_inside_only_once(client, officer_a, admin):
    qd = register(client, officer_a).json()
    r = register(client, officer_a)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "truck_already_inside"
    assert "queue" in r.json()["detail"]["message"]
    enter(client, officer_a, qd["id"])
    assert "inside" in register(client, officer_a).json()["detail"]["message"]
    warnings = client.get("/api/admin/events", params={"group": "warnings"},
                          headers=admin.headers).json()
    assert [w["kind"] for w in warnings] == ["already_inside", "already_inside"]


def test_lookup_says_where_the_visit_stands(client, officer_a):
    def look():
        return client.get("/api/trucks/lookup", params={"plate": "ABC123XY"},
                          headers=officer_a.headers).json()
    assert look() is None
    qd = register(client, officer_a).json()
    assert look()["open_entry_id"] == qd["id"] and look()["open_entry_status"] == "queued"
    enter(client, officer_a, qd["id"])
    assert look()["open_entry_status"] == "on_site"
    out(client, officer_a, qd["id"])
    assert look()["open_entry_id"] is None and look()["open_entry_status"] is None


def test_off_duty_nobody_moves_a_truck(client, officer_a):
    qd = register(client, officer_a).json()
    client.post("/api/duty/off", json={}, headers=officer_a.headers)
    assert enter(client, officer_a, qd["id"]).json()["detail"]["code"] == "not_on_duty"
    assert leave(client, officer_a, qd["id"]).json()["detail"]["code"] == "not_on_duty"
    client.post("/api/duty/on", json={"id": str(uuid.uuid4()), "gate": 1},
                headers=officer_a.headers)
    assert enter(client, officer_a, qd["id"]).status_code == 200


def test_trucks_of_other_facilities_are_out_of_reach(client, officer_a, officer_b):
    qd = register(client, officer_a).json()
    assert enter(client, officer_b, qd["id"]).status_code == 404
    assert leave(client, officer_b, qd["id"]).status_code == 404


def test_the_gate_stands_for_where_the_officer_stood(client, officer_a, admin):
    client.put("/api/admin/facilities/CNG-A/gates", json={"gate_count": 3},
               headers=admin.headers)
    client.post("/api/duty/change-gate", json={"id": str(uuid.uuid4()), "gate": 2},
                headers=officer_a.headers)
    qd = register(client, officer_a).json()
    assert qd["queued_gate"] == 2
    client.post("/api/duty/change-gate", json={"id": str(uuid.uuid4()), "gate": 3},
                headers=officer_a.headers)
    e = enter(client, officer_a, qd["id"]).json()
    assert e["queued_gate"] == 2 and e["gate_in"] == 3


# ---- warnings the server raises ----

def _age_queue(entry_id, hours):
    with create_session() as db:
        row = db.get(TruckEntry, uuid.UUID(entry_id))
        assert row is not None
        row.signed_in_at = utcnow() - timedelta(hours=hours)
        db.commit()


def _warnings(client, admin):
    return client.get("/api/admin/events", params={"group": "warnings"},
                      headers=admin.headers).json()


def test_a_truck_queued_too_long_is_reported_once(client, officer_a, admin):
    old = register(client, officer_a, plate_number="OLD111").json()
    fresh = register(client, officer_a, plate_number="NEW222").json()
    inside = register(client, officer_a, plate_number="IN333").json()
    enter(client, officer_a, inside["id"])
    _age_queue(old["id"], Settings.QUEUED_WARN_HOURS + 1)
    _age_queue(fresh["id"], Settings.QUEUED_WARN_HOURS - 1)
    _age_queue(inside["id"], Settings.QUEUED_WARN_HOURS + 1)  # in the queue long, but inside now
    with create_session() as db:
        assert len(event_service.check_warnings(db)) == 1
    with create_session() as db:
        assert event_service.check_warnings(db) == []
    w = _warnings(client, admin)
    assert [x["kind"] for x in w] == ["queued_too_long"]
    assert w[0]["summary"] == (
        f"Truck OLD111 has been in the queue for {Settings.QUEUED_WARN_HOURS}+ hours.")
    assert w[0]["facility_code"] == "CNG-A"


def test_a_queued_truck_is_never_left_inside(client, officer_a, admin):
    qd = register(client, officer_a).json()
    _age_queue(qd["id"], Settings.LEFT_INSIDE_HOURS + 5)
    with create_session() as db:
        event_service.check_warnings(db)
    assert [w["kind"] for w in _warnings(client, admin)] == ["queued_too_long"]


def test_an_officer_on_duty_too_long_is_reported_once_per_shift(client, officer_a, admin):
    client.put("/api/admin/facilities/CNG-A/gates", json={"gate_count": 2}, headers=admin.headers)
    with create_session() as db:
        row = db.query(DutyEntry).one()
        row.on_duty_at = utcnow() - timedelta(hours=Settings.DUTY_WARN_HOURS + 1)
        db.commit()
    with create_session() as db:
        assert len(event_service.check_warnings(db)) == 1
    # moving to another gate is the same shift: no second warning
    client.post("/api/duty/change-gate", json={"id": str(uuid.uuid4()), "gate": 2},
                headers=officer_a.headers)
    with create_session() as db:
        assert event_service.check_warnings(db) == []
    w = [x for x in _warnings(client, admin) if x["kind"] == "on_duty_too_long"]
    assert len(w) == 1
    assert w[0]["summary"] == (
        f"Test OFF-001 has been on duty for {Settings.DUTY_WARN_HOURS}+ hours (gate 1).")


def _leave_gate_at(minutes_ago):
    with create_session() as db:
        row = db.query(DutyEntry).one()
        row.on_duty_at = utcnow() - timedelta(hours=2)
        row.off_duty_at = utcnow() - timedelta(minutes=minutes_ago)
        row.ended_how = "off"
        db.commit()


def test_a_gate_nobody_covers_is_reported_after_a_grace_period(client, admin):
    make_actor(client, code="OFF-001", facility="CNG-A")
    _leave_gate_at(Settings.GATE_UNMANNED_MINUTES - 5)  # left a moment ago: handover
    with create_session() as db:
        assert event_service.check_warnings(db) == []
    _leave_gate_at(Settings.GATE_UNMANNED_MINUTES + 5)
    with create_session() as db:
        assert len(event_service.check_warnings(db)) == 1
    with create_session() as db:
        assert event_service.check_warnings(db) == []
    w = _warnings(client, admin)
    assert [x["kind"] for x in w] == ["gate_unmanned"]
    assert w[0]["summary"] == (
        f"Gate 1 at CNG-A has had nobody on duty for {Settings.GATE_UNMANNED_MINUTES}+ minutes.")


def test_a_gate_someone_took_over_is_not_unmanned(client, admin):
    make_actor(client, code="OFF-001", facility="CNG-A")
    _leave_gate_at(Settings.GATE_UNMANNED_MINUTES + 5)
    make_actor(client, code="OFF-002", facility="CNG-A")  # on duty at gate 1 again
    with create_session() as db:
        assert event_service.check_warnings(db) == []


def test_a_gate_that_was_never_manned_is_not_reported(client, admin):
    make_actor(client, code="OFF-001", facility="CNG-A", on_duty=False)
    with create_session() as db:
        assert event_service.check_warnings(db) == []


def test_a_queued_truck_is_let_in_on_the_signature_on_file(client, officer_a):
    plate = "rep-777 zz"
    first = register(client, officer_a, plate_number=plate).json()
    assert enter(client, officer_a, first["id"], signature=None).status_code == 422  # none yet
    drawn = enter(client, officer_a, first["id"]).json()
    assert drawn["signature_in_reused"] is False
    client.post(f"/api/trucks/entries/{first['id']}/sign-out", json={}, headers=officer_a.headers)
    again = register(client, officer_a, plate_number=plate).json()
    e = enter(client, officer_a, again["id"], signature=None).json()
    assert e["status"] == "on_site" and e["has_signature"] is True
    assert e["signature_in_reused"] is True
