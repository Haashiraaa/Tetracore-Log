# tests/api/routes/test_visitors.py

"""Visitor log: sign in, sign out, signatures, scoping."""

import base64
import uuid

URL = "/api/visitors/entries"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PNG_B64 = base64.b64encode(PNG).decode()


def fresh_phone():
    return "0803" + str(uuid.uuid4().int)[:7]


def payload(**over):
    return {"id": str(uuid.uuid4()), "full_name": "Ngozi Eze", "company": "Acme Ltd",
            "purpose": "Delivery", "items_received": "2 boxes of filters",
            "phone": fresh_phone(), "signature": PNG_B64, **over}


def sign_in(client, who, **over):
    return client.post(URL, json=payload(**over), headers=who.headers)


def sign_out(client, who, entry_id, body=None):
    return client.post(f"{URL}/{entry_id}/sign-out",
                       json={"signature": PNG_B64, **(body or {})}, headers=who.headers)


def test_requires_login(client):
    assert client.get(URL).status_code == 401
    assert client.post(URL, json=payload()).status_code == 401


def test_sign_in_records_the_fields(client, officer_a):
    r = sign_in(client, officer_a)
    assert r.status_code == 201
    e = r.json()
    assert (e["full_name"], e["company"], e["purpose"]) == ("Ngozi Eze", "Acme Ltd", "Delivery")
    assert e["items_received"] == "2 boxes of filters" and e["phone"].startswith("0803")
    assert e["facility_code"] == "CNG-A" and e["signed_in_by_name"]
    assert e["signed_out_at"] is None
    assert e["has_signature"] is True and e["has_signature_out"] is False


def test_sign_in_is_idempotent(client, officer_a):
    body = payload()
    first = client.post(URL, json=body, headers=officer_a.headers)
    again = client.post(URL, json=body, headers=officer_a.headers)
    assert (first.status_code, again.status_code) == (201, 200)
    assert first.json() == again.json()
    assert len(client.get(URL, headers=officer_a.headers).json()) == 1


def test_entry_id_cannot_be_reused_across_facilities(client, officer_a, officer_b):
    body = payload()
    assert client.post(URL, json=body, headers=officer_a.headers).status_code == 201
    assert client.post(URL, json=body, headers=officer_b.headers).status_code == 409


def test_validation(client, officer_a):
    assert sign_in(client, officer_a, full_name="x").status_code == 422
    assert sign_in(client, officer_a, signed_in_at="2026-11-01T08:00:00").status_code == 422


def test_sign_out_flow_and_first_sign_out_wins(client, officer_a):
    eid = sign_in(client, officer_a).json()["id"]
    r = sign_out(client, officer_a, eid, {"signed_out_at": "2026-11-01T18:00:00+01:00"})
    assert r.status_code == 200 and r.json()["signed_out_by_name"]
    first_out = r.json()["signed_out_at"]
    again = sign_out(client, officer_a, eid, {"signed_out_at": "2026-11-02T18:00:00+01:00"})
    assert again.json()["signed_out_at"] == first_out
    assert sign_out(client, officer_a, eid).status_code == 200  # empty body is fine


def test_sign_out_errors(client, officer_a, officer_b):
    eid = sign_in(client, officer_a).json()["id"]
    assert sign_out(client, officer_b, eid).status_code == 404  # another facility's entry
    assert sign_out(client, officer_a, str(uuid.uuid4())).status_code == 404


def test_both_signatures_round_trip_and_are_scoped(client, officer_a, officer_b, cso):
    eid = sign_in(client, officer_a, signature="data:image/png;base64," + PNG_B64).json()["id"]
    out = sign_out(client, officer_a, eid, {"signature": PNG_B64}).json()
    assert out["has_signature"] is True and out["has_signature_out"] is True
    for side in ("in", "out"):
        got = client.get(f"{URL}/{eid}/signature", params={"side": side},
                         headers=officer_a.headers)
        assert got.status_code == 200 and got.content == PNG
        assert got.headers["content-type"] == "image/png"
    assert client.get(f"{URL}/{eid}/signature", headers=cso.headers).status_code == 200
    assert client.get(f"{URL}/{eid}/signature", headers=officer_b.headers).status_code == 404


def test_missing_or_bad_signatures(client, officer_a):
    eid = sign_in(client, officer_a).json()["id"]
    assert client.get(f"{URL}/{eid}/signature", params={"side": "out"},
                      headers=officer_a.headers).status_code == 404
    assert client.get(f"{URL}/{eid}/signature", params={"side": "sideways"},
                      headers=officer_a.headers).status_code == 422
    bad = sign_in(client, officer_a, signature=base64.b64encode(b"not a png").decode())
    assert bad.status_code == 422 and bad.json()["detail"]["code"] == "invalid_signature"
    assert sign_out(client, officer_a, eid, {"signature": "!!"}).status_code == 422


def test_only_accounts_with_a_facility_write(client, manager_a, cso, admin):
    assert sign_in(client, manager_a).status_code == 201
    for who in (cso, admin):
        assert sign_in(client, who).status_code == 403
        assert sign_out(client, who, str(uuid.uuid4())).status_code == 403


def test_each_facility_sees_only_its_own(client, officer_a, officer_b):
    mine = sign_in(client, officer_a).json()["id"]
    sign_in(client, officer_b)
    assert [e["id"] for e in client.get(URL, headers=officer_a.headers).json()] == [mine]


def test_admin_and_global_accounts_see_every_facility(client, officer_a, officer_b, admin, cso):
    sign_in(client, officer_a)
    sign_in(client, officer_b)
    for who in (admin, cso):
        assert len(client.get(URL, headers=who.headers).json()) == 2


def test_open_filter_and_paging(client, officer_a):
    inside = sign_in(client, officer_a).json()["id"]
    gone = sign_in(client, officer_a).json()["id"]
    sign_out(client, officer_a, gone)
    still = client.get(URL, params={"open": True}, headers=officer_a.headers).json()
    assert [e["id"] for e in still] == [inside]
    assert client.get(URL, params={"limit": 0}, headers=officer_a.headers).status_code == 422
    assert len(client.get(URL, params={"limit": 1}, headers=officer_a.headers).json()) == 1


def test_name_phone_and_signature_are_required_the_rest_may_be_blank(client, officer_a):
    r = sign_in(client, officer_a, company="", purpose="  ", items_received="")
    assert r.status_code == 201
    e = r.json()
    assert (e["company"], e["purpose"], e["items_received"]) == (None,) * 3
    for missing in ("full_name", "phone", "signature"):
        body = payload()
        del body[missing]
        assert client.post(URL, json=body, headers=officer_a.headers).status_code == 422
    assert sign_in(client, officer_a, phone="").status_code == 422
    assert sign_in(client, officer_a, phone="12").status_code == 422


def test_the_same_visitor_can_visit_twice(client, officer_a):
    first, second = sign_in(client, officer_a), sign_in(client, officer_a)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


# ---- full names, phone numbers, finding a returning visitor ----

def test_full_name_needs_two_words_and_is_tidied(client, officer_a):
    assert sign_in(client, officer_a, full_name="Ngozi").status_code == 422
    assert sign_in(client, officer_a, full_name="  Ngozi   Eze ").json()["full_name"] == "Ngozi Eze"


def test_phone_is_stored_in_one_canonical_form(client, officer_a):
    for typed in ("0803 111 2222", "+234 803 111 2222", "2348031112222", "(0803)-111-2222"):
        e = sign_in(client, officer_a, phone=typed).json()
        assert e["phone"] == "08031112222"
        sign_out(client, officer_a, e["id"])


def test_lookup_finds_a_returning_visitor_however_the_phone_is_typed(client, officer_a):
    def look(phone):
        return client.get("/api/visitors/lookup", params={"phone": phone},
                          headers=officer_a.headers)

    assert look("08031112222").json() is None
    e = sign_in(client, officer_a, phone="08031112222", company="Acme Ltd").json()
    found = look("+234 803 111 2222").json()
    assert (found["full_name"], found["company"], found["phone"]) == (
        "Ngozi Eze", "Acme Ltd", "08031112222")
    assert found["open_entry_id"] == e["id"]
    sign_out(client, officer_a, e["id"])
    assert look("08031112222").json()["open_entry_id"] is None
    assert look("abc").status_code == 422


def test_lookup_uses_the_latest_visit_and_stays_in_the_facility(client, officer_a, officer_b):
    sign_out(client, officer_a, sign_in(
        client, officer_a, phone="08031112222", company="Old Co").json()["id"])
    sign_in(client, officer_a, phone="08031112222", company="New Co")
    seen = client.get("/api/visitors/lookup", params={"phone": "08031112222"},
                      headers=officer_a.headers).json()
    assert seen["company"] == "New Co"
    assert client.get("/api/visitors/lookup", params={"phone": "08031112222"},
                      headers=officer_b.headers).json() is None


def test_lookup_is_for_accounts_with_a_facility(client, cso, admin):
    for who in (cso, admin):
        assert client.get("/api/visitors/lookup", params={"phone": "08031112222"},
                          headers=who.headers).status_code == 403


def test_one_sign_in_at_a_time(client, officer_a):
    first = sign_in(client, officer_a, phone="08031112222").json()
    again = sign_in(client, officer_a, phone="+2348031112222")
    assert again.status_code == 409 and again.json()["detail"]["code"] == "already_inside"
    sign_out(client, officer_a, first["id"])
    assert sign_in(client, officer_a, phone="08031112222").status_code == 201


def test_signatures_are_required_both_ways(client, officer_a):
    eid = sign_in(client, officer_a).json()["id"]
    out = f"{URL}/{eid}/sign-out"
    assert client.post(out, json={}, headers=officer_a.headers).status_code == 422
    assert client.post(out, headers=officer_a.headers).status_code == 422
    assert client.get(URL, params={"open": True}, headers=officer_a.headers).json()
