# tests/api/routes/test_waybill.py

"""Waybill log: a courier brings goods. Items, optional vehicle, signature reuse, scoping."""

import base64
import uuid

import pytest

URL = "/api/waybill/entries"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PNG_B64 = base64.b64encode(PNG).decode()
ITEMS = [{"name": "Skid", "quantity": 1, "unit": None}]


def fresh_phone():
    return "0803" + str(uuid.uuid4().int)[:7]


def payload(**over):
    return {"id": str(uuid.uuid4()), "full_name": "Musa Courier", "phone": fresh_phone(),
            "items": ITEMS, "signature": PNG_B64, **over}


def sign_in(client, who, **over):
    return client.post(URL, json=payload(**over), headers=who.headers)


def sign_out(client, who, entry_id, body=None):
    return client.post(f"{URL}/{entry_id}/sign-out", json=body or {}, headers=who.headers)


def test_requires_login(client):
    assert client.get(URL).status_code == 401
    assert client.post(URL, json=payload()).status_code == 401


def test_a_courier_on_foot_has_no_plate(client, officer_a):
    r = sign_in(client, officer_a, items=[{"name": "Skid", "quantity": 1, "unit": "pallet"}])
    assert r.status_code == 201, r.text
    e = r.json()
    assert (e["full_name"], e["came_by_vehicle"], e["plate_number"]) == (
        "Musa Courier", False, None)
    assert e["items"] == [{"name": "Skid", "quantity": 1, "unit": "pallet"}]
    assert e["phone"].startswith("+234803")
    assert e["facility_code"] == "CNG-A" and e["signed_out_at"] is None


def test_a_courier_with_a_vehicle_gives_its_plate(client, officer_a):
    e = sign_in(client, officer_a, came_by_vehicle=True, plate_number="lag 123 ab").json()
    assert (e["came_by_vehicle"], e["plate_number"]) == (True, "LAG123AB")


def test_vehicle_and_plate_go_together(client, officer_a):
    assert sign_in(client, officer_a, came_by_vehicle=True).status_code == 422
    assert sign_in(client, officer_a, came_by_vehicle=True, plate_number="").status_code == 422
    assert sign_in(client, officer_a, plate_number="LAG123AB").status_code == 422
    assert sign_in(client, officer_a, came_by_vehicle=True, plate_number="!").status_code == 422


@pytest.mark.parametrize("bad", ["yes", 1, 0, None, "true"])
def test_came_by_vehicle_must_be_a_real_flag(client, officer_a, bad):
    assert sign_in(client, officer_a, came_by_vehicle=bad).status_code == 422


@pytest.mark.parametrize("items", [
    [], "Skid", None,
    [{"name": "", "quantity": 1}], [{"name": "Skid", "quantity": "1"}],
    [{"name": "Skid", "quantity": 0}], [{"name": "Skid"}],
    [{"name": f"Thing {i}", "quantity": 1} for i in range(31)],
])
def test_at_least_one_valid_item_is_needed(client, officer_a, items):
    assert sign_in(client, officer_a, items=items).status_code == 422


def test_several_items_keep_their_order(client, officer_a):
    items = [{"name": "Skid", "quantity": 1, "unit": None},
             {"name": "Oil", "quantity": 20, "unit": "litres"}]
    assert sign_in(client, officer_a, items=items).json()["items"] == items


def test_validation(client, officer_a):
    assert sign_in(client, officer_a, full_name="").status_code == 422
    assert sign_in(client, officer_a, phone="abc").status_code == 422
    assert sign_in(client, officer_a, signed_in_at="2026-11-01T08:00:00").status_code == 422


def test_sign_in_is_idempotent_and_ids_do_not_cross_facilities(client, officer_a, officer_b):
    body = payload()
    first = client.post(URL, json=body, headers=officer_a.headers)
    again = client.post(URL, json=body, headers=officer_a.headers)
    assert (first.status_code, again.status_code) == (201, 200)
    assert first.json() == again.json()
    assert client.post(URL, json=body, headers=officer_b.headers).status_code == 409


def test_one_sign_in_at_a_time_per_phone(client, officer_a):
    phone = fresh_phone()
    first = sign_in(client, officer_a, phone=phone).json()
    again = sign_in(client, officer_a, phone=phone)
    assert again.status_code == 409 and again.json()["detail"]["code"] == "already_inside"
    sign_out(client, officer_a, first["id"])
    assert sign_in(client, officer_a, phone=phone).status_code == 201


def test_sign_out_and_first_sign_out_wins(client, officer_a, officer_b):
    eid = sign_in(client, officer_a).json()["id"]
    assert sign_out(client, officer_b, eid).status_code == 404  # another facility's entry
    r = sign_out(client, officer_a, eid, {"signed_out_at": "2026-11-01T18:00:00+01:00"})
    assert r.status_code == 200 and r.json()["signed_out_by_name"]
    first_out = r.json()["signed_out_at"]
    again = sign_out(client, officer_a, eid, {"signed_out_at": "2026-11-02T18:00:00+01:00"})
    assert again.json()["signed_out_at"] == first_out


# ---- signatures are kept and reused, like visitors ----

def test_sign_out_without_a_signature_reuses_the_sign_in_one(client, officer_a):
    eid = sign_in(client, officer_a).json()["id"]
    r = sign_out(client, officer_a, eid)
    assert r.json()["has_signature_out"] is True and r.json()["signature_out_reused"] is True
    got = client.get(f"{URL}/{eid}/signature", params={"side": "out"}, headers=officer_a.headers)
    assert got.status_code == 200 and got.content == PNG


def test_a_returning_courier_does_not_have_to_sign_again(client, officer_a, officer_b):
    phone = fresh_phone()
    first = sign_in(client, officer_a, phone=phone).json()
    sign_out(client, officer_a, first["id"])
    body = payload(phone=phone)
    del body["signature"]
    r = client.post(URL, json=body, headers=officer_a.headers)
    assert r.status_code == 201, r.text
    assert r.json()["has_signature"] is True and r.json()["signature_in_reused"] is True
    # another facility has never seen this courier: they must sign there
    body = payload(phone=phone)
    del body["signature"]
    assert client.post(URL, json=body, headers=officer_b.headers).status_code == 422


def test_a_new_courier_must_sign(client, officer_a):
    body = payload()
    del body["signature"]
    r = client.post(URL, json=body, headers=officer_a.headers)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "invalid_signature"


# ---- lookup and search ----

def test_lookup_prefills_the_last_vehicle(client, officer_a):
    phone = fresh_phone()
    sign_in(client, officer_a, phone=phone, came_by_vehicle=True, plate_number="LAG123AB")
    found = client.get("/api/waybill/lookup", params={"phone": phone},
                       headers=officer_a.headers).json()
    assert found["full_name"] == "Musa Courier" and found["came_by_vehicle"] is True
    assert found["plate_number"] == "LAG123AB" and found["open_entry_id"] is not None
    assert found["has_signature"] is True
    assert client.get("/api/waybill/lookup", params={"phone": fresh_phone()},
                      headers=officer_a.headers).json() is None


def test_search_by_phone(client, officer_a):
    sign_in(client, officer_a, phone="0803 777 1111")
    hits = client.get("/api/waybill/search", params={"q": "0803777"},
                      headers=officer_a.headers).json()
    assert [h["phone"] for h in hits] == ["+2348037771111"]
    assert client.get("/api/waybill/search", params={"q": "08"},
                      headers=officer_a.headers).status_code == 422


# ---- who writes, who sees ----

def test_only_accounts_with_a_facility_write(client, manager_a, cso, admin):
    assert sign_in(client, manager_a).status_code == 201
    for who in (cso, admin):
        assert sign_in(client, who).status_code == 403


def test_nobody_logs_a_courier_off_duty(client):
    from tests._helpers import make_actor
    resting = make_actor(client, code="OFF-009", facility="CNG-A", on_duty=False)
    assert sign_in(client, resting).status_code == 409


def test_each_facility_sees_its_own_and_global_accounts_see_all(
        client, officer_a, officer_b, cso):
    mine = sign_in(client, officer_a).json()["id"]
    sign_in(client, officer_b)
    assert [e["id"] for e in client.get(URL, headers=officer_a.headers).json()] == [mine]
    assert len(client.get(URL, headers=cso.headers).json()) == 2
    still = client.get(URL, params={"open": True}, headers=officer_a.headers).json()
    assert [e["id"] for e in still] == [mine]


def test_a_courier_sign_in_is_announced_by_name(client, officer_a, admin):
    from tests.api.routes.test_events import feed
    sign_in(client, officer_a, full_name="Ngozi Courier")
    found = {e["kind"]: e["summary"] for e in feed(client, admin)}
    assert found["waybill_in"] == "Ngozi Courier signed in."
