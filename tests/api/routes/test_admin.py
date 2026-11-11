

# tests/api/routes/test_admin.py

import pytest

from tests._helpers import PIN, login, login_response, make_actor

FAC = "CNG-LAG-01"  # the first facility mkfac makes in Lagos


def mkfac(client, who, state="Lagos", name="Station"):
    return client.post("/api/admin/facilities", headers=who.headers,
                       json={"state": state, "name": name})


def test_admin_routes_are_admin_only(client, officer_a, cso):
    assert client.get("/api/admin/facilities").status_code == 401
    for who in (officer_a, cso):
        r = client.get("/api/admin/facilities", headers=who.headers)
        assert r.status_code == 403 and r.json(
        )["detail"]["code"] == "forbidden"


def test_facility_codes_are_issued_per_state(client, admin):
    made = [mkfac(client, admin, st) for st in
            ("Lagos", "lagos", "Benue", "  akwa   ibom ", "Federal Capital Territory", "Lagos")]
    assert all(r.status_code == 201 for r in made)
    assert [r.json()["code"] for r in made] == [
        "CNG-LAG-01", "CNG-LAG-02", "CNG-BEN-01", "CNG-AKW-01", "CNG-FCT-01", "CNG-LAG-03"]
    assert made[3].json()["state"] == "Akwa Ibom"  # stored with the proper spelling
    listed = client.get("/api/admin/facilities", headers=admin.headers).json()
    assert [f["code"] for f in listed] == sorted(r.json()["code"] for r in made)


def test_a_facility_number_is_never_reused(client, admin):
    from sqlalchemy import delete

    from backend.src.db.orm.tables import Facility
    from backend.src.db.session import create_session
    assert mkfac(client, admin).json()["code"] == "CNG-LAG-01"
    with create_session() as db:  # even if the facility is removed behind our back
        db.execute(delete(Facility))
        db.commit()
    assert mkfac(client, admin).json()["code"] == "CNG-LAG-02"


def test_the_code_cannot_be_chosen_or_made_up(client, admin):
    r = client.post("/api/admin/facilities", headers=admin.headers,
                    json={"state": "Lagos", "name": "Sneaky", "code": "MY-OWN-CODE"})
    assert r.status_code == 201 and r.json()["code"] == "CNG-LAG-01"
    for bad in ("Narnia", "", "L"):
        assert mkfac(client, admin, bad).status_code == 422
    no_state = client.post("/api/admin/facilities", headers=admin.headers,
                           json={"name": "No state"})
    assert no_state.status_code == 422


def test_a_taken_code_is_skipped(client, admin):
    from tests._helpers import make_account
    make_account(code="OFF-001", facility="CNG-LAG-01")  # seeded by hand
    assert mkfac(client, admin).json()["code"] == "CNG-LAG-02"


def test_states_list(client, admin, officer_a):
    rows = client.get("/api/admin/states", headers=admin.headers).json()
    assert len(rows) == 37 and {"name": "Lagos", "abbrev": "LAG"} in rows
    assert client.get("/api/admin/states", headers=officer_a.headers).status_code == 403


def test_create_officers_auto_codes(client, admin):
    mkfac(client, admin)
    made = []
    for name, role in [("Guard One", "Officer"), ("Guard Two", "Officer"),
                       ("Manager One", "facility_manager")]:
        r = client.post("/api/admin/officers", headers=admin.headers,
                        json={"facility_code": FAC.lower(), "full_name": name, "role": role})
        assert r.status_code == 201, r.text
        assert r.headers["cache-control"] == "no-store"
        body = r.json()
        assert len(body["temp_pin"]) == 6 and body["temp_pin"].isdigit()
        assert body["officer"]["must_change_pin"] is True
        made.append((body["officer"]["officer_code"], body["officer"]["role"]))
    # one code series per facility, whatever the role label is
    assert made == [("OFF-001", "Officer"), ("OFF-002", "Officer"),
                    ("OFF-003", "facility_manager")]


def test_an_officer_needs_a_full_name(client, admin):
    mkfac(client, admin)
    for bad in ("Madu", " ", ""):
        r = client.post("/api/admin/officers", headers=admin.headers,
                        json={"facility_code": FAC, "full_name": bad})
        assert r.status_code == 422


def test_role_is_a_free_label(client, admin):
    mkfac(client, admin)
    r = client.post("/api/admin/officers", headers=admin.headers,
                    json={"facility_code": FAC, "full_name": "Shift Boss",
                          "role": "  Shift Supervisor "})
    assert r.status_code == 201, r.text
    assert r.json()["officer"]["role"] == "Shift Supervisor"
    # even a label that used to mean something is just a label now
    r = client.post("/api/admin/officers", headers=admin.headers,
                    json={"facility_code": FAC, "full_name": "Not Special", "role": "cso"})
    assert r.status_code == 201
    assert r.json()["officer"]["facility_code"] == FAC
    assert r.json()["officer"]["sees_all_facilities"] is False
    # left out: the default label
    r = client.post("/api/admin/officers", headers=admin.headers,
                    json={"facility_code": FAC, "full_name": "Default Role"})
    assert r.json()["officer"]["role"] == "Officer"


@pytest.mark.parametrize("bad", ["", "   ", "x" * 33])
def test_blank_or_overlong_role_is_rejected(client, admin, bad):
    mkfac(client, admin)
    r = client.post("/api/admin/officers", headers=admin.headers,
                    json={"facility_code": FAC, "full_name": "Bad Role", "role": bad})
    assert r.status_code == 422


def test_create_officer_unknown_facility(client, admin):
    r = client.post("/api/admin/officers", headers=admin.headers,
                    json={"facility_code": "NOPE-1", "full_name": "Ghost Rider"})
    assert r.status_code == 404


def test_the_api_can_never_make_an_admin(client, admin):
    mkfac(client, admin)
    r = client.post("/api/admin/officers", headers=admin.headers,
                    json={"facility_code": FAC, "full_name": "Sneaky Pete",
                          "role": "admin", "is_admin": True})
    assert r.status_code == 201
    assert r.json()["officer"]["is_admin"] is False
    h = login(client, r.json()["officer"]["officer_code"], FAC, r.json()["temp_pin"])
    assert client.get("/api/admin/facilities", headers=h).status_code == 403


def test_temp_pin_flow(client, admin):
    mkfac(client, admin)
    r = client.post("/api/admin/officers", headers=admin.headers,
                    json={"facility_code": FAC, "full_name": "New Guard"})
    code, pin = r.json()["officer"]["officer_code"], r.json()["temp_pin"]
    h = login(client, code, FAC, pin)
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
