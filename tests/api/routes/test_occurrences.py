# tests/api/routes/test_occurrences.py

"""Events log: an officer's own notes. Time, officer and gate are automatic; the signature is
the officer's duty signature, reused."""

import base64
import uuid

import pytest
from sqlalchemy import update

from backend.src.db.orm.tables import DutyEntry
from backend.src.db.session import create_session
from tests._helpers import make_actor
from tests.api.routes.test_events import feed

URL = "/api/occurrences"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PNG_B64 = base64.b64encode(PNG).decode()
OTHER_PNG = b"\x89PNG\r\n\x1a\n" + b"\x01" * 64


def sign_on_duty(officer, png=PNG):
    """The officer drew a signature when going on duty."""
    with create_session() as db:
        db.execute(update(DutyEntry).where(DutyEntry.officer_id == officer.id)
                   .values(signature_in=png))
        db.commit()


def note(client, who, text="Fuel tanker queue reached the main road.", **over):
    body = {"id": str(uuid.uuid4()), "note": text, **over}
    return client.post(URL, json=body, headers=who.headers)


def test_requires_login(client):
    assert client.get(URL).status_code == 401
    assert client.post(URL, json={"id": str(uuid.uuid4()), "note": "hello"}).status_code == 401


def test_a_note_carries_time_officer_gate_and_the_reused_signature(client, officer_a):
    sign_on_duty(officer_a)
    r = note(client, officer_a)
    assert r.status_code == 201, r.text
    n = r.json()
    assert n["note"] == "Fuel tanker queue reached the main road."
    assert n["officer_name"] == "Test OFF-001" and n["officer_id"] == str(officer_a.id)
    assert n["gate"] == 1 and n["facility_code"] == "CNG-A" and n["logged_at"]
    assert n["has_signature"] is True and n["signature_reused"] is True
    got = client.get(f"{URL}/{n['id']}/signature", headers=officer_a.headers)
    assert got.status_code == 200 and got.content == PNG


def test_the_latest_duty_signature_is_the_one_used(client, officer_a):
    sign_on_duty(officer_a, PNG)
    with create_session() as db:  # a later shift, signed differently
        first = db.query(DutyEntry).filter_by(officer_id=officer_a.id).one()
        db.add(DutyEntry(
            id=uuid.uuid4(), shift_id=uuid.uuid4(), facility_id=first.facility_id,
            officer_id=officer_a.id, gate=2, on_duty_at=first.on_duty_at.replace(
                year=first.on_duty_at.year + 1), signature_in=OTHER_PNG, off_duty_at=None))
        first.off_duty_at = first.on_duty_at
        db.commit()
    n = note(client, officer_a).json()
    assert client.get(f"{URL}/{n['id']}/signature", headers=officer_a.headers).content == OTHER_PNG


def test_a_drawn_signature_is_used_and_not_marked_reused(client, officer_a):
    n = note(client, officer_a, signature=PNG_B64).json()  # never signed on duty
    assert n["has_signature"] is True and n["signature_reused"] is False


def test_with_no_signature_anywhere_the_officer_must_sign(client, officer_a):
    assert client.get(f"{URL}/signature-on-file", headers=officer_a.headers).json() == {
        "has_signature": False}
    r = note(client, officer_a)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "invalid_signature"
    sign_on_duty(officer_a)
    assert client.get(f"{URL}/signature-on-file", headers=officer_a.headers).json() == {
        "has_signature": True}


def test_a_bad_signature_is_refused(client, officer_a):
    bad = base64.b64encode(b"not a png").decode()
    assert note(client, officer_a, signature=bad).status_code == 422


@pytest.mark.parametrize("bad", ["", "  ", "hi", None, 5, ["x"], "x" * 2001])
def test_the_note_must_be_real_text(client, officer_a, bad):
    sign_on_duty(officer_a)
    assert note(client, officer_a, text=bad).status_code == 422


def test_the_server_decides_who_and_when_not_the_request(client, officer_a):
    sign_on_duty(officer_a)
    n = note(client, officer_a, officer_id=str(uuid.uuid4()), facility_id=str(uuid.uuid4()),
             gate=9).json()
    assert n["officer_id"] == str(officer_a.id) and n["gate"] == 1
    assert n["facility_code"] == "CNG-A"
    assert note(client, officer_a, logged_at="2026-11-01T08:00:00").status_code == 422
    stamped = note(client, officer_a, logged_at="2026-11-01T08:00:00+01:00").json()
    assert stamped["logged_at"].startswith("2026-11-01T07:00:00")


def test_a_retry_returns_the_same_note_and_ids_do_not_cross_facilities(
        client, officer_a, officer_b):
    sign_on_duty(officer_a)
    sign_on_duty(officer_b)
    body = {"id": str(uuid.uuid4()), "note": "Gate 1 barrier stuck."}
    first = client.post(URL, json=body, headers=officer_a.headers)
    again = client.post(URL, json=body, headers=officer_a.headers)
    assert (first.status_code, again.status_code) == (201, 200)
    assert first.json() == again.json()
    assert client.post(URL, json=body, headers=officer_b.headers).status_code == 409
    assert len(client.get(URL, headers=officer_a.headers).json()) == 1


def test_nobody_writes_a_note_off_duty(client):
    resting = make_actor(client, code="OFF-009", facility="CNG-A", on_duty=False)
    r = note(client, resting, signature=PNG_B64)
    assert r.status_code == 409


def test_only_accounts_with_a_facility_write(client, cso, admin):
    for who in (cso, admin):
        assert note(client, who, signature=PNG_B64).status_code == 403


def test_each_facility_sees_its_own_and_global_accounts_see_all(
        client, officer_a, officer_b, cso, admin):
    sign_on_duty(officer_a)
    sign_on_duty(officer_b)
    mine = note(client, officer_a).json()["id"]
    note(client, officer_b)
    assert [n["id"] for n in client.get(URL, headers=officer_a.headers).json()] == [mine]
    for who in (cso, admin):
        assert len(client.get(URL, headers=who.headers).json()) == 2
    assert client.get(f"{URL}/{mine}/signature", headers=officer_b.headers).status_code == 404
    assert client.get(f"{URL}/{mine}/signature", headers=cso.headers).status_code == 200


def test_listing_is_newest_first_and_pages(client, officer_a):
    sign_on_duty(officer_a)
    note(client, officer_a, text="First thing", logged_at="2026-11-01T08:00:00+01:00")
    note(client, officer_a, text="Second thing", logged_at="2026-11-01T09:00:00+01:00")
    got = client.get(URL, headers=officer_a.headers).json()
    assert [n["note"] for n in got] == ["Second thing", "First thing"]
    assert len(client.get(URL, params={"limit": 1}, headers=officer_a.headers).json()) == 1
    assert client.get(URL, params={"limit": 0}, headers=officer_a.headers).status_code == 422


def test_an_event_is_announced_to_admins_with_the_officers_name(client, officer_a, admin):
    sign_on_duty(officer_a)
    note(client, officer_a, text="Smell of gas near pump 3.")
    found = {e["kind"]: e["summary"] for e in feed(client, admin)}
    assert found["event_logged"] == "Test OFF-001 logged an event: Smell of gas near pump 3."
