

# tests/api/routes/test_admin.py

import pytest

from tests._helpers import PIN, login, login_response, make_actor


def mkfac(client, who, code="CNG-N"):
    return client.post("/api/admin/facilities", headers=who.headers,
                       json={"code": code, "name": f"Station {code}"})


def test_admin_routes_are_admin_only(client, officer_a, cso):
    assert client.get("/api/admin/facilities").status_code == 401
    for who in (officer_a, cso):
        r = client.get("/api/admin/facilities", headers=who.headers)
        assert r.status_code == 403 and r.json(
        )["detail"]["code"] == "forbidden"


def test_facilities(client, admin):
    assert mkfac(client, admin).status_code == 201
    # case-insensitive dup
    assert mkfac(client, admin, "cng-n").status_code == 409
    bad = client.post("/api/admin/facilities", headers=admin.headers,
                      json={"code": "bad code!", "name": "Nope"})
    assert bad.status_code == 422
    listed = client.get("/api/admin/facilities", headers=admin.headers).json()
    assert [f["code"] for f in listed] == ["CNG-N"]


def test_create_officers_auto_codes(client, admin):
    mkfac(client, admin)
    made = []
    for name, role in [("Guard One", "officer"), ("Guard Two", "officer"),
                       ("Manager One", "facility_manager")]:
        r = client.post("/api/admin/officers", headers=admin.headers,
                        json={"facility_code": "cng-n", "full_name": name, "role": role})
        assert r.status_code == 201, r.text
        assert r.headers["cache-control"] == "no-store"
        body = r.json()
        assert len(body["temp_pin"]) == 6 and body["temp_pin"].isdigit()
        assert body["officer"]["must_change_pin"] is True
        made.append((body["officer"]["officer_code"], body["officer"]["role"]))
    # one code series per facility, whatever the role label is
    assert made == [("OFF-001", "officer"), ("OFF-002", "officer"),
                    ("OFF-003", "facility_manager")]


def test_role_is_a_free_label(client, admin):
    mkfac(client, admin)
    r = client.post("/api/admin/officers", headers=admin.headers,
                    json={"facility_code": "CNG-N", "full_name": "Shift Boss",
                          "role": "  Shift Supervisor "})
    assert r.status_code == 201, r.text
    assert r.json()["officer"]["role"] == "Shift Supervisor"
    # even a label that used to mean something is just a label now
    r = client.post("/api/admin/officers", headers=admin.headers,
                    json={"facility_code": "CNG-N", "full_name": "Not Special", "role": "cso"})
    assert r.status_code == 201
    assert r.json()["officer"]["facility_code"] == "CNG-N"
    assert r.json()["officer"]["sees_all_facilities"] is False
    # left out: the default label
    r = client.post("/api/admin/officers", headers=admin.headers,
                    json={"facility_code": "CNG-N", "full_name": "Default Role"})
    assert r.json()["officer"]["role"] == "officer"


@pytest.mark.parametrize("bad", ["", "   ", "x" * 33])
def test_blank_or_overlong_role_is_rejected(client, admin, bad):
    mkfac(client, admin)
    r = client.post("/api/admin/officers", headers=admin.headers,
                    json={"facility_code": "CNG-N", "full_name": "Bad Role", "role": bad})
    assert r.status_code == 422


def test_create_officer_unknown_facility(client, admin):
    r = client.post("/api/admin/officers", headers=admin.headers,
                    json={"facility_code": "NOPE-1", "full_name": "Ghost"})
    assert r.status_code == 404


def test_the_api_can_never_make_an_admin(client, admin):
    mkfac(client, admin)
    r = client.post("/api/admin/officers", headers=admin.headers,
                    json={"facility_code": "CNG-N", "full_name": "Sneaky",
                          "role": "admin", "is_admin": True})
    assert r.status_code == 201
    assert r.json()["officer"]["is_admin"] is False
    h = login(client, r.json()["officer"]["officer_code"], "CNG-N", r.json()["temp_pin"])
    assert client.get("/api/admin/facilities", headers=h).status_code == 403


def test_temp_pin_flow(client, admin):
    mkfac(client, admin)
    r = client.post("/api/admin/officers", headers=admin.headers,
                    json={"facility_code": "CNG-N", "full_name": "New Guard"})
    code, pin = r.json()["officer"]["officer_code"], r.json()["temp_pin"]
    h = login(client, code, "CNG-N", pin)
    assert client.get(
        "/api/auth/me", headers=h).json()["must_change_pin"] is True
    blocked = client.get("/api/trucks/lookup",
                         params={"plate": "ABC123"}, headers=h)
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "must_change_pin"
    r = client.post("/api/auth/change-pin", headers=h,
                    json={"current_pin": pin, "new_pin": "739150"})
    assert r.status_code == 204
    ok = client.get("/api/trucks/lookup",
                    params={"plate": "ABC123"}, headers=h)
    assert ok.status_code == 200


def test_list_officers_hides_admins(
        client, admin, cso, officer_a, manager_a, officer_b):
    rows = client.get("/api/admin/officers", headers=admin.headers).json()
    assert {(o["facility_code"], o["officer_code"]) for o in rows} == {
        ("CNG-A", "OFF-001"), ("CNG-A", "MGR-001"), ("CNG-B", "OFF-001"),
        (None, "CSO-001")}  # a global non-admin account is manageable too
    only_b = client.get("/api/admin/officers", params={"facility_code": "cng-b"},
                        headers=admin.headers).json()
    assert [(o["facility_code"], o["officer_code"])
            for o in only_b] == [("CNG-B", "OFF-001")]
    assert all("is_active" in o for o in rows)


def test_reset_pin(client, admin, officer_a):
    r = client.post(
        f"/api/admin/officers/{officer_a.id}/reset-pin", headers=admin.headers)
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    temp = r.json()["temp_pin"]
    assert r.json()["officer_code"] == "OFF-001"
    assert login_response(client, "OFF-001", "CNG-A", PIN).status_code == 401
    h = login(client, "OFF-001", "CNG-A", temp)
    assert client.get(
        "/api/auth/me", headers=h).json()["must_change_pin"] is True
    # the old phone session was killed
    assert client.get(
        "/api/auth/me", headers=officer_a.headers).status_code == 401


def test_disable_enable_revoke(client, admin, officer_a):
    oid = officer_a.id
    assert client.post(f"/api/admin/officers/{oid}/revoke-sessions",
                       headers=admin.headers).status_code == 204
    r = client.get("/api/auth/me", headers=officer_a.headers)
    assert r.status_code == 401 and r.json(
    )["detail"]["code"] == "session_revoked"
    assert login_response(
        client, "OFF-001", "CNG-A").status_code == 200  # still enabled

    assert client.post(f"/api/admin/officers/{oid}/disable",
                       headers=admin.headers).status_code == 204
    assert login_response(client, "OFF-001", "CNG-A").status_code == 401
    assert client.post(f"/api/admin/officers/{oid}/enable",
                       headers=admin.headers).status_code == 204
    assert login_response(client, "OFF-001", "CNG-A").status_code == 200


ACTIONS = ("reset-pin", "disable", "enable", "revoke-sessions")


def test_admin_cannot_touch_any_admin(client, admin):
    other = make_actor(client, code="ADM-002", role="admin", is_admin=True)
    for target in (admin.id, other.id):  # another admin, and itself
        for action in ACTIONS:
            r = client.post(
                f"/api/admin/officers/{target}/{action}", headers=admin.headers)
            assert r.status_code == 404, (target, action)


def test_admin_manages_global_accounts_too(client, admin, cso):
    r = client.post(f"/api/admin/officers/{cso.id}/reset-pin", headers=admin.headers)
    assert r.status_code == 200 and r.json()["officer_code"] == "CSO-001"
    assert client.post(f"/api/admin/officers/{cso.id}/disable",
                       headers=admin.headers).status_code == 204
    assert login_response(client, "CSO-001").status_code == 401
    assert client.post(f"/api/admin/officers/{cso.id}/enable",
                       headers=admin.headers).status_code == 204


def test_unknown_officer_is_404(client, admin):
    r = client.post("/api/admin/officers/00000000-0000-0000-0000-000000000000/reset-pin",
                    headers=admin.headers)
    assert r.status_code == 404
