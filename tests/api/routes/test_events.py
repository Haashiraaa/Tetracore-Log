# tests/api/routes/test_events.py

"""The global admin's notification feed: what gets recorded, who may read it, unread
counts, the "left inside" check, and browser push."""

import base64
import uuid
from datetime import timedelta

import pytest

from backend.src.api import event_service, push
from backend.src.config.settings import Settings
from backend.src.db.orm.tables import StaffEntry, TruckEntry, VisitorEntry
from backend.src.db.session import create_session
from backend.src.security.tokens import utcnow
from tests._helpers import make_actor

PNG_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64).decode()
FEED = "/api/admin/events"


def person(**over):
    return {"id": str(uuid.uuid4()), "full_name": "Ada Okoro", "capacity": "Cashier",
            "phone": "0803" + str(uuid.uuid4().int)[:7], "signature": PNG_B64, **over}


def truck(**over):
    return {"id": str(uuid.uuid4()), "plate_number": "abc-123 xy", "driver_name": "Musa Ibrahim",
            "driver_phone": "08030000000", "signature": PNG_B64, "enter_now": True, **over}


def sign_in(client, who, log, body):
    return client.post(f"/api/{log}/entries", json=body, headers=who.headers)


def sign_out(client, who, log, entry_id):
    return client.post(f"/api/{log}/entries/{entry_id}/sign-out",
                       json={"signature": PNG_B64}, headers=who.headers)


def feed(client, who, **params):
    r = client.get(FEED, params=params, headers=who.headers)
    assert r.status_code == 200, r.text
    return r.json()


def kinds(events):
    return [e["kind"] for e in reversed(events)]  # oldest first reads like a story


# ---- what gets recorded ----


def test_every_gate_sign_in_and_out_is_recorded(client, officer_a, admin):
    t = sign_in(client, officer_a, "trucks", truck()).json()
    v = sign_in(client, officer_a, "visitors", person(full_name="Ngozi Eze")).json()
    s = sign_in(client, officer_a, "staff", person()).json()
    for log, e in (("trucks", t), ("visitors", v), ("staff", s)):
        assert sign_out(client, officer_a, log, e["id"]).status_code == 200

    events = feed(client, admin)
    assert kinds(events) == ["truck_in", "visitor_in", "staff_in",
                             "truck_out", "visitor_out", "staff_out"]
    first = events[-1]
    assert first["summary"] == "Truck ABC123XY signed in, driver Musa Ibrahim."
    assert first["facility_code"] == "CNG-A" and first["actor_name"] == "Test OFF-001"
    assert first["severity"] == "info" and first["entry_id"] == t["id"]
    assert events[0]["summary"] == "Ada Okoro signed out."
    assert events[2]["summary"] == "Truck ABC123XY signed out."


def test_retries_are_not_news(client, officer_a, admin):
    body = person()
    entry = sign_in(client, officer_a, "staff", body).json()
    assert sign_in(client, officer_a, "staff", body).status_code == 200  # replay of the same id
    sign_out(client, officer_a, "staff", entry["id"])
    sign_out(client, officer_a, "staff", entry["id"])  # a second sign-out changes nothing
    assert kinds(feed(client, admin)) == ["staff_in", "staff_out"]


def test_signing_in_someone_already_inside_is_a_warning(client, officer_a, admin):
    phone = "08031112222"
    sign_in(client, officer_a, "visitors", person(phone=phone))
    assert sign_in(client, officer_a, "visitors", person(phone=phone)).status_code == 409
    sign_in(client, officer_a, "trucks", truck())
    assert sign_in(client, officer_a, "trucks", truck()).status_code == 409

    warnings = feed(client, admin, group="warnings")
    assert [w["kind"] for w in warnings] == ["already_inside", "already_inside"]
    assert {w["severity"] for w in warnings} == {"warning"}
    assert warnings[0]["summary"] == (
        "Truck ABC123XY tried to sign in but is already queued or inside.")
    assert warnings[1]["summary"] == "Ada Okoro tried to sign in but is already inside."
    # the refused attempt made no sign-in
    assert kinds(feed(client, admin, group="gate")) == ["visitor_in", "truck_in"]


def test_admin_changes_are_recorded_with_who_did_them(client, admin):
    h = admin.headers
    state = client.get("/api/admin/states", headers=h).json()[0]["name"]
    fac = client.post("/api/admin/facilities", json={"state": state, "name": "Ikeja Station"},
                      headers=h).json()
    made = client.post("/api/admin/officers", headers=h, json={
        "facility_code": fac["code"], "full_name": "Bashir Lawal"}).json()
    oid = made["officer"]["id"]
    for action in ("reset-pin", "disable", "enable", "revoke-sessions"):
        done = client.post(f"/api/admin/officers/{oid}/{action}", headers=h)
        assert done.status_code in (200, 204)

    events = feed(client, admin, group="admin")
    assert kinds(events) == ["facility_added", "officer_added", "officer_pin_reset",
                             "officer_disabled", "officer_enabled", "sessions_revoked"]
    assert events[-1].get("facility_code") == fac["code"]
    assert f"Facility {fac['code']} (Ikeja Station) was added with 1 gate." == events[-1]["summary"]
    assert {e["actor_name"] for e in events} == {"Test ADM-001"}
    assert all(e["severity"] == "info" for e in events)


# ---- reading ----


def test_only_admins_read_the_feed(client, officer_a, cso, admin):
    for path in ("", "/summary"):
        for who in (officer_a, cso):
            assert client.get(FEED + path, headers=who.headers).status_code == 403
    assert client.post(FEED + "/read", json={}, headers=officer_a.headers).status_code == 403
    assert client.get(FEED).status_code == 401
    assert client.get(FEED, headers=admin.headers).status_code == 200


def test_filters_paging_and_polling(client, officer_a, officer_b, admin):
    sign_in(client, officer_a, "staff", person())
    sign_in(client, officer_b, "visitors", person(capacity=None))
    sign_in(client, officer_a, "trucks", truck())
    everything = feed(client, admin)
    assert [e["facility_code"] for e in reversed(everything)] == ["CNG-A", "CNG-B", "CNG-A"]
    assert [e["id"] for e in everything] == sorted((e["id"] for e in everything), reverse=True)

    assert {e["facility_code"] for e in feed(client, admin, facility_code="cng-b")} == {"CNG-B"}
    assert kinds(feed(client, admin, group="admin")) == []
    assert kinds(feed(client, admin, group="warnings")) == []
    page = feed(client, admin, limit=2)
    assert [e["id"] for e in page] == [everything[0]["id"], everything[1]["id"]]
    older = feed(client, admin, limit=2, before_id=page[-1]["id"])
    assert [e["id"] for e in older] == [everything[2]["id"]]
    assert [e["id"] for e in feed(client, admin, after_id=everything[2]["id"])] == [
        everything[0]["id"], everything[1]["id"]]
    assert feed(client, admin, after_id=everything[0]["id"]) == []
    assert client.get(FEED, params={"group": "nope"}, headers=admin.headers).status_code == 422


def test_unread_counts_start_at_zero_and_follow_the_admin(client, officer_a, admin):
    sign_in(client, officer_a, "staff", person())  # before this admin ever looked
    url = FEED + "/summary"
    first = client.get(url, headers=admin.headers).json()
    assert first["unread"] == 0 and first["last_read_id"] == first["latest_id"] > 0

    sign_in(client, officer_a, "staff", person())
    sign_in(client, officer_a, "visitors", person(capacity=None))
    now = client.get(url, headers=admin.headers).json()
    assert now["unread"] == 2 and now["latest_id"] == first["latest_id"] + 2

    # reading up to the first of the two leaves one unread
    done = client.post(FEED + "/read", json={"up_to_id": first["latest_id"] + 1},
                       headers=admin.headers).json()
    assert done["unread"] == 1
    # an older mark never makes events unread again
    older = client.post(FEED + "/read", json={"up_to_id": 1}, headers=admin.headers)
    assert older.json()["unread"] == 1
    assert client.post(FEED + "/read", json={}, headers=admin.headers).json()["unread"] == 0


def test_each_admin_has_their_own_read_position(client, officer_a, admin):
    other = make_actor(client, code="ADM-002", role="admin", is_admin=True)
    client.get(FEED + "/summary", headers=admin.headers)
    client.get(FEED + "/summary", headers=other.headers)
    sign_in(client, officer_a, "staff", person())
    client.post(FEED + "/read", json={}, headers=admin.headers)
    assert client.get(FEED + "/summary", headers=admin.headers).json()["unread"] == 0
    assert client.get(FEED + "/summary", headers=other.headers).json()["unread"] == 1


# ---- left inside ----


def _age(model, entry_id, hours):
    with create_session() as db:
        row = db.get(model, uuid.UUID(entry_id))
        assert row is not None
        row.signed_in_at = utcnow() - timedelta(hours=hours)
        if model is TruckEntry:  # a truck counts from when it came in, not when it queued
            row.entered_at = row.signed_in_at
        db.commit()


def test_people_left_inside_overnight_are_reported_once(client, officer_a, admin):
    t = sign_in(client, officer_a, "trucks", truck()).json()
    v = sign_in(client, officer_a, "visitors", person(full_name="Ngozi Eze")).json()
    s = sign_in(client, officer_a, "staff", person()).json()
    for model, e in ((TruckEntry, t), (VisitorEntry, v), (StaffEntry, s)):
        _age(model, e["id"], Settings.LEFT_INSIDE_HOURS + 1)

    with create_session() as db:
        assert len(event_service.check_warnings(db)) == 2  # staff are never "left inside"
    with create_session() as db:
        assert event_service.check_warnings(db) == []  # already reported: nothing new

    found = feed(client, admin, group="warnings")
    assert {w["kind"] for w in found} == {"left_inside"}
    assert sorted(w["summary"] for w in found) == sorted([
        f"Truck ABC123XY is still inside, {Settings.LEFT_INSIDE_HOURS}+ hours after entering.",
        f"Ngozi Eze is still inside, {Settings.LEFT_INSIDE_HOURS}+ hours after signing in."])
    assert all(w["actor_name"] is None and w["facility_code"] == "CNG-A" for w in found)


# ---- browser push ----


@pytest.fixture
def push_on(monkeypatch):
    """Push configured, the pool runs inline, and webpush records instead of sending."""
    monkeypatch.setattr(Settings, "VAPID_PUBLIC_KEY", "PUBKEY")
    monkeypatch.setattr(Settings, "VAPID_PRIVATE_KEY", "PRIVKEY")
    monkeypatch.setattr(Settings, "VAPID_SUBJECT", "mailto:ops@example.com")

    class Inline:
        def submit(self, fn, *args):
            fn(*args)
    monkeypatch.setattr(push, "_pool", Inline())
    sent: list[dict] = []
    monkeypatch.setattr(push, "webpush", lambda **kw: sent.append(kw))
    return sent


def subscribe(client, who, endpoint="https://push.example/abc"):
    return client.post("/api/admin/push/subscribe", headers=who.headers, json={
        "endpoint": endpoint, "keys": {"p256dh": "P" * 20, "auth": "A" * 10}})


def test_push_is_off_until_keys_are_set(client, admin, officer_a):
    config = client.get("/api/admin/push/config", headers=admin.headers)
    assert config.json() == {"public_key": None}
    assert client.get("/api/admin/push/config", headers=officer_a.headers).status_code == 403
    subscribe(client, admin)
    sign_in(client, officer_a, "staff", person())  # nothing to send with, and nothing breaks
    assert len(feed(client, admin)) == 1


def test_push_goes_to_every_subscribed_admin_browser(client, officer_a, admin, push_on):
    assert client.get("/api/admin/push/config", headers=admin.headers).json() == {
        "public_key": "PUBKEY"}
    other = make_actor(client, code="ADM-002", role="admin", is_admin=True)
    assert subscribe(client, admin, "https://push.example/phone").status_code == 204
    assert subscribe(client, admin, "https://push.example/laptop").status_code == 204
    assert subscribe(client, other, "https://push.example/other").status_code == 204

    sign_in(client, officer_a, "staff", person())
    assert sorted(kw["subscription_info"]["endpoint"] for kw in push_on) == [
        "https://push.example/laptop", "https://push.example/other",
        "https://push.example/phone"]
    one = push_on[0]
    assert one["vapid_private_key"] == "PRIVKEY"
    assert one["vapid_claims"] == {"sub": "mailto:ops@example.com"}
    import json
    body = json.loads(one["data"])
    assert body["title"] == "CNG-A" and body["body"] == "Ada Okoro signed in."
    assert body["url"] == "/notifications"


def test_warnings_are_pushed_as_warnings(client, officer_a, admin, push_on):
    subscribe(client, admin)
    phone = "08031112222"
    sign_in(client, officer_a, "visitors", person(phone=phone))
    push_on.clear()
    sign_in(client, officer_a, "visitors", person(phone=phone))
    import json
    body = json.loads(push_on[0]["data"])
    assert body["title"] == "Warning · CNG-A" and "already inside" in body["body"]


def test_a_gone_browser_is_forgotten_and_a_slow_one_does_not_break_the_gate(
        client, officer_a, admin, push_on, monkeypatch):
    from pywebpush import WebPushException

    class Resp:
        status_code = 410
    subscribe(client, admin, "https://push.example/dead")
    subscribe(client, admin, "https://push.example/alive")

    def fake(**kw):
        if kw["subscription_info"]["endpoint"].endswith("dead"):
            raise WebPushException("gone", response=Resp())
        push_on.append(kw)
    monkeypatch.setattr(push, "webpush", fake)

    assert sign_in(client, officer_a, "staff", person()).status_code == 201
    assert [kw["subscription_info"]["endpoint"] for kw in push_on] == ["https://push.example/alive"]
    push_on.clear()
    sign_in(client, officer_a, "staff", person())
    assert len(push_on) == 1  # the dead one is gone for good

    def explode(**_kw):
        raise RuntimeError("push service down")
    monkeypatch.setattr(push, "webpush", explode)
    assert sign_in(client, officer_a, "staff", person()).status_code == 201


def test_unsubscribing_stops_push_and_a_disabled_admin_gets_none(
        client, officer_a, admin, push_on):
    other = make_actor(client, code="ADM-002", role="admin", is_admin=True)
    subscribe(client, admin, "https://push.example/one")
    subscribe(client, other, "https://push.example/two")
    r = client.post("/api/admin/push/unsubscribe", headers=admin.headers,
                    json={"endpoint": "https://push.example/one"})
    assert r.status_code == 204
    # another admin cannot remove it for you, and unknown endpoints are not an error
    assert client.post("/api/admin/push/unsubscribe", headers=admin.headers,
                       json={"endpoint": "https://push.example/two"}).status_code == 204
    sign_in(client, officer_a, "staff", person())
    assert [kw["subscription_info"]["endpoint"] for kw in push_on] == ["https://push.example/two"]

    with create_session() as db:
        from backend.src.db.orm.tables import Officer
        row = db.get(Officer, other.id)
        assert row is not None
        row.is_active = False
        db.commit()
    push_on.clear()
    sign_in(client, officer_a, "staff", person())
    assert push_on == []


def test_subscribing_validates_the_browsers_shape(client, admin):
    r = client.post("/api/admin/push/subscribe", headers=admin.headers,
                    json={"endpoint": "x", "keys": {}})
    assert r.status_code == 422


def test_push_test_reports_what_happened(client, admin, officer_a, push_on, monkeypatch):
    assert client.post("/api/admin/push/test", headers=officer_a.headers).status_code == 403
    assert client.post("/api/admin/push/test", headers=admin.headers).json() == {
        "subscriptions": 0, "sent": 0, "failed": []}
    subscribe(client, admin, "https://push.example/phone")
    push_on.clear()
    body = client.post("/api/admin/push/test", headers=admin.headers).json()
    assert body == {"subscriptions": 1, "sent": 1, "failed": []}
    assert push_on[0]["subscription_info"]["endpoint"] == "https://push.example/phone"

    from pywebpush import WebPushException

    class Resp:
        status_code = 403

    def refuse(**kw):
        raise WebPushException("keys", response=Resp())
    monkeypatch.setattr(push, "webpush", refuse)
    body = client.post("/api/admin/push/test", headers=admin.headers).json()
    assert body["sent"] == 0 and "keys" in body["failed"][0]


def test_push_test_needs_push_to_be_set_up(client, admin):
    assert client.post("/api/admin/push/test", headers=admin.headers).status_code == 409
