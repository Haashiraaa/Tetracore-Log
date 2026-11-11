# tests/api/routes/test_duty.py

import base64
import uuid
from datetime import timedelta

from backend.src.db.orm.tables import DutyEntry
from backend.src.db.session import create_session
from backend.src.security.tokens import utcnow
from tests._helpers import make_actor

PNG_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64).decode()


def go_on(client, who, gate=1, **over):
    body = {"id": str(uuid.uuid4()), "gate": gate, **over}
    return client.post("/api/duty/on", json=body, headers=who.headers)


def go_off(client, who, **over):
    return client.post("/api/duty/off", json=over, headers=who.headers)


def change(client, who, gate):
    return client.post("/api/duty/change-gate", json={"id": str(uuid.uuid4()), "gate": gate},
                       headers=who.headers)


def status(client, who):
    r = client.get("/api/duty", headers=who.headers)
    assert r.status_code == 200, r.text
    return r.json()


def set_gates(client, admin, code, n):
    return client.put(f"/api/admin/facilities/{code}/gates", json={"gate_count": n},
                      headers=admin.headers)


def visitor(**over):
    return {"id": str(uuid.uuid4()), "full_name": "Ngozi Eze", "phone": "08031112222",
            "signature": PNG_B64, **over}


def kinds(client, admin):
    r = client.get("/api/admin/events", headers=admin.headers)
    return [e["kind"] for e in reversed(r.json())]


# ---- going on and off ----

def test_go_on_and_off(client, admin):
    who = make_actor(client, code="OFF-009", facility="CNG-A", on_duty=False)
    assert status(client, who) == {"facility_code": "CNG-A", "gate_count": 1, "current": None}
    r = go_on(client, who, signature=PNG_B64)
    assert r.status_code == 201, r.text
    e = r.json()
    assert e["gate"] == 1 and e["officer_name"] == "Test OFF-009"
    assert e["off_duty_at"] is None and e["has_signature"] is True
    assert e["started_how"] == "on" and e["shift_id"] == e["id"]
    assert status(client, who)["current"]["id"] == e["id"]
    off = go_off(client, who, signature=PNG_B64)
    assert off.status_code == 200 and off.json()["current"] is None
    row = client.get("/api/duty/entries", headers=who.headers).json()[0]
    assert row["off_duty_at"] is not None and row["ended_how"] == "off"
    assert row["has_signature_out"] is True
    assert kinds(client, admin) == ["officer_on_duty", "officer_off_duty"]


def test_the_signature_is_optional(client):
    who = make_actor(client, code="OFF-009", facility="CNG-A", on_duty=False)
    r = go_on(client, who)
    assert r.status_code == 201 and r.json()["has_signature"] is False
    assert go_off(client, who).status_code == 200


def test_go_on_is_idempotent_and_never_twice(client):
    who = make_actor(client, code="OFF-009", facility="CNG-A", on_duty=False)
    body = {"id": str(uuid.uuid4()), "gate": 1}
    first = client.post("/api/duty/on", json=body, headers=who.headers)
    again = client.post("/api/duty/on", json=body, headers=who.headers)
    assert first.status_code == 201 and again.status_code == 200
    second = go_on(client, who)  # a new stretch while still on duty
    assert second.status_code == 409 and second.json()["detail"]["code"] == "already_on_duty"


def test_going_off_when_off_changes_nothing(client, admin):
    who = make_actor(client, code="OFF-009", facility="CNG-A", on_duty=False)
    assert go_off(client, who).status_code == 200
    assert kinds(client, admin) == []


def test_the_gate_must_exist(client, admin):
    who = make_actor(client, code="OFF-009", facility="CNG-A", on_duty=False)
    r = go_on(client, who, gate=2)  # CNG-A has 1 gate
    assert r.status_code == 409 and r.json()["detail"]["code"] == "invalid_gate"
    assert set_gates(client, admin, "CNG-A", 4).status_code == 200
    assert go_on(client, who, gate=4).status_code == 201
    assert go_on(client, who, gate=0).status_code == 422
    assert go_on(client, who, gate=21).status_code == 422


def test_only_facility_accounts_log_duty(client, admin, cso):
    assert client.get("/api/duty", headers=cso.headers).status_code == 403
    assert client.post("/api/duty/on", json={"id": str(uuid.uuid4()), "gate": 1},
                       headers=admin.headers).status_code == 403


def test_a_duty_id_cannot_be_reused_across_facilities(client):
    a = make_actor(client, code="OFF-009", facility="CNG-A", on_duty=False)
    b = make_actor(client, code="OFF-009", facility="CNG-B", on_duty=False)
    body = {"id": str(uuid.uuid4()), "gate": 1}
    assert client.post("/api/duty/on", json=body, headers=a.headers).status_code == 201
    assert client.post("/api/duty/on", json=body, headers=b.headers).status_code == 409


# ---- change gate ----

def test_change_gate_closes_one_stretch_and_opens_another(client, admin):
    who = make_actor(client, code="OFF-009", facility="CNG-A", on_duty=False)
    assert set_gates(client, admin, "CNG-A", 3).status_code == 200
    first = go_on(client, who, gate=1).json()
    moved = change(client, who, 3)
    assert moved.status_code == 201, moved.text
    now = moved.json()
    assert now["gate"] == 3 and now["started_how"] == "moved"
    assert now["shift_id"] == first["id"]  # the same shift
    rows = client.get("/api/duty/entries", headers=who.headers).json()
    old = next(r for r in rows if r["id"] == first["id"])
    assert old["ended_how"] == "moved" and old["off_duty_at"] is not None
    assert status(client, who)["current"]["gate"] == 3
    assert kinds(client, admin)[-2:] == ["officer_on_duty", "officer_gate_changed"]


def test_change_gate_rules(client, admin):
    who = make_actor(client, code="OFF-009", facility="CNG-A", on_duty=False)
    assert set_gates(client, admin, "CNG-A", 2).status_code == 200
    assert change(client, who, 2).json()["detail"]["code"] == "not_on_duty"
    go_on(client, who, gate=1)
    assert change(client, who, 1).json()["detail"]["code"] == "invalid_gate"   # already there
    assert change(client, who, 3).json()["detail"]["code"] == "invalid_gate"   # no such gate


# ---- on duty is required to log anything ----

def test_nobody_logs_anything_off_duty(client):
    who = make_actor(client, code="OFF-009", facility="CNG-A", on_duty=False)
    staff = visitor(phone="08035556666", capacity="Cashier")
    for log, body in (("visitors", visitor()), ("staff", staff),
                      ("trucks", {"id": str(uuid.uuid4()), "plate_number": "ABC123",
                                  "driver_name": "Musa Ibrahim"})):
        r = client.post(f"/api/{log}/entries", json=body, headers=who.headers)
        assert r.status_code == 409 and r.json()["detail"]["code"] == "not_on_duty", log
    assert client.get("/api/visitors/entries", headers=who.headers).json() == []


def test_the_gate_is_recorded_on_the_entry(client, admin):
    who = make_actor(client, code="OFF-009", facility="CNG-A", on_duty=False)
    assert set_gates(client, admin, "CNG-A", 3).status_code == 200
    go_on(client, who, gate=2)
    v = client.post("/api/visitors/entries", json=visitor(), headers=who.headers).json()
    assert v["gate_in"] == 2 and v["gate_out"] is None
    change(client, who, 3)
    out = client.post(f"/api/visitors/entries/{v['id']}/sign-out",
                      json={"signature": PNG_B64}, headers=who.headers).json()
    assert out["gate_in"] == 2 and out["gate_out"] == 3


def test_sign_out_needs_duty_but_a_replay_does_not(client):
    who = make_actor(client, code="OFF-009", facility="CNG-A")
    v = client.post("/api/visitors/entries", json=visitor(), headers=who.headers).json()
    go_off(client, who)
    r = client.post(f"/api/visitors/entries/{v['id']}/sign-out",
                    json={"signature": PNG_B64}, headers=who.headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "not_on_duty"
    go_on(client, who)
    assert client.post(f"/api/visitors/entries/{v['id']}/sign-out",
                       json={"signature": PNG_B64}, headers=who.headers).status_code == 200
    go_off(client, who)
    again = client.post(f"/api/visitors/entries/{v['id']}/sign-out",
                        json={"signature": PNG_B64}, headers=who.headers)
    assert again.status_code == 200  # already closed: nothing to change, nothing to refuse


def test_one_officer_going_off_does_not_stop_another(client):
    a = make_actor(client, code="OFF-001", facility="CNG-A")
    b = make_actor(client, code="OFF-002", facility="CNG-A")
    go_off(client, a)
    assert client.post("/api/visitors/entries", json=visitor(),
                       headers=b.headers).status_code == 201


# ---- reading ----

def test_who_is_on_duty_now_is_scoped(client, admin, cso):
    make_actor(client, code="OFF-001", facility="CNG-A")
    make_actor(client, code="OFF-001", facility="CNG-B")
    a = make_actor(client, code="OFF-002", facility="CNG-A", on_duty=False)
    assert len(client.get("/api/duty/now", headers=a.headers).json()) == 1
    assert len(client.get("/api/duty/now", headers=admin.headers).json()) == 2
    assert len(client.get("/api/duty/now", headers=cso.headers).json()) == 2


def test_signatures_download_and_are_scoped(client):
    a = make_actor(client, code="OFF-009", facility="CNG-A", on_duty=False)
    b = make_actor(client, code="OFF-009", facility="CNG-B")
    e = go_on(client, a, signature=PNG_B64).json()
    go_off(client, a, signature=PNG_B64)
    url = f"/api/duty/entries/{e['id']}/signature"
    assert client.get(url, headers=a.headers).headers["content-type"] == "image/png"
    assert client.get(url, params={"side": "out"}, headers=a.headers).status_code == 200
    assert client.get(url, headers=b.headers).status_code == 404


# ---- the admin ----

def test_an_admin_can_end_a_forgotten_duty(client, admin):
    who = make_actor(client, code="OFF-009", facility="CNG-A")
    r = client.post(f"/api/admin/officers/{who.id}/end-duty", headers=admin.headers)
    assert r.status_code == 204
    assert status(client, who)["current"] is None
    row = client.get("/api/duty/entries", headers=who.headers).json()[0]
    assert row["ended_how"] == "admin"
    assert kinds(client, admin) == ["officer_off_duty"]
    # off duty already: a quiet no-op
    assert client.post(f"/api/admin/officers/{who.id}/end-duty",
                       headers=admin.headers).status_code == 204
    assert kinds(client, admin) == ["officer_off_duty"]


def test_disabling_an_officer_takes_them_off_duty(client, admin):
    who = make_actor(client, code="OFF-009", facility="CNG-A")
    assert client.post(f"/api/admin/officers/{who.id}/disable",
                       headers=admin.headers).status_code == 204
    with create_session() as db:
        rows = db.query(DutyEntry).all()
        assert len(rows) == 1 and rows[0].ended_how == "admin"
    assert kinds(client, admin) == ["officer_off_duty", "officer_disabled"]


def test_gates_cannot_shrink_under_someone_on_duty(client, admin):
    make_actor(client, code="OFF-009", facility="CNG-A", on_duty=False)
    assert set_gates(client, admin, "CNG-A", 4).status_code == 200
    who = make_actor(client, code="OFF-010", facility="CNG-A", on_duty=False)
    go_on(client, who, gate=4)
    r = set_gates(client, admin, "CNG-A", 3)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "invalid_gate"
    go_off(client, who)
    assert set_gates(client, admin, "CNG-A", 3).status_code == 200
    assert kinds(client, admin).count("gates_changed") == 2


def test_gates_are_set_when_a_facility_is_created(client, admin):
    state = client.get("/api/admin/states", headers=admin.headers).json()[0]["name"]
    made = client.post("/api/admin/facilities", headers=admin.headers,
                       json={"state": state, "name": "Ikeja Station", "gate_count": 4})
    assert made.status_code == 201 and made.json()["gate_count"] == 4
    bad = client.post("/api/admin/facilities", headers=admin.headers,
                      json={"state": state, "name": "Other Station", "gate_count": 0})
    assert bad.status_code == 422
    assert set_gates(client, admin, "CNG-NOPE", 2).status_code == 404
    other = make_actor(client, code="OFF-001", facility="CNG-A", on_duty=False)
    assert set_gates(client, other, "CNG-A", 2).status_code == 403  # not an admin


def test_old_duty_is_still_there_after_the_shift(client):
    who = make_actor(client, code="OFF-009", facility="CNG-A")
    with create_session() as db:
        row = db.query(DutyEntry).one()
        row.on_duty_at = utcnow() - timedelta(hours=3)
        db.commit()
    go_off(client, who)
    rows = client.get("/api/duty/entries", params={"open": "true"}, headers=who.headers).json()
    assert rows == []
    assert len(client.get("/api/duty/entries", headers=who.headers).json()) == 1
