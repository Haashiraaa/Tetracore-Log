# tests/api/routes/test_visitors.py

"""Visitor log: sign in, sign out, signatures, scoping."""

import base64
import uuid

URL = "/api/visitors/entries"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PNG_B64 = base64.b64encode(PNG).decode()


def payload(**over):
    return {"id": str(uuid.uuid4()), "full_name": "Ngozi Eze", "company": "Acme Ltd",
            "purpose": "Delivery", "items_received": "2 boxes of filters",
            "phone": "08031112222", **over}


def sign_in(client, who, **over):
    return client.post(URL, json=payload(**over), headers=who.headers)


def sign_out(client, who, entry_id, body=None):
    return client.post(f"{URL}/{entry_id}/sign-out", json=body or {}, headers=who.headers)


def test_requires_login(client):
    assert client.get(URL).status_code == 401
    assert client.post(URL, json=payload()).status_code == 401


def test_sign_in_records_the_fields(client, officer_a):
    r = sign_in(client, officer_a)
    assert r.status_code == 201
    e = r.json()
    assert (e["full_name"], e["company"], e["purpose"]) == ("Ngozi Eze", "Acme Ltd", "Delivery")
    assert (e["items_received"], e["phone"]) == ("2 boxes of filters", "08031112222")
    assert e["facility_code"] == "CNG-A" and e["signed_in_by_name"]
    assert e["signed_out_at"] is None
    assert e["has_signature"] is False and e["has_signature_out"] is False


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


def test_only_the_name_is_required_and_blanks_become_null(client, officer_a):
    r = sign_in(client, officer_a, company="", purpose="  ", items_received="", phone="")
    assert r.status_code == 201
    e = r.json()
    assert (e["company"], e["purpose"], e["items_received"], e["phone"]) == (None,) * 4
    only_id = {"id": str(uuid.uuid4())}
    assert client.post(URL, json=only_id, headers=officer_a.headers).status_code == 422


def test_the_same_visitor_can_visit_twice(client, officer_a):
    first, second = sign_in(client, officer_a), sign_in(client, officer_a)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
