# tests/api/routes/test_staff.py

"""Staff log: sign in, sign out, signatures, scoping."""

import base64
import uuid

URL = "/api/staff/entries"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PNG_B64 = base64.b64encode(PNG).decode()


def fresh_phone():
    return "0803" + str(uuid.uuid4().int)[:7]


def payload(**over):
    return {"id": str(uuid.uuid4()), "full_name": "Ada Okoro", "capacity": "Cashier",
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
    assert (e["full_name"], e["capacity"]) == ("Ada Okoro", "Cashier")
    assert e["phone"].startswith("+234803")
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
    assert sign_in(client, officer_a, full_name="").status_code == 422
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


# ---- capacity, full names, phone, finding a returning person ----

def test_capacity_is_free_text_and_required(client, officer_a):
    assert sign_in(client, officer_a, capacity="Weekend relief attendant").json()[
        "capacity"] == "Weekend relief attendant"
    body = payload()
    del body["capacity"]
    assert client.post(URL, json=body, headers=officer_a.headers).status_code == 422
    assert sign_in(client, officer_a, capacity="").status_code == 422


def test_full_name_phone_and_signature_are_required(client, officer_a):
    assert sign_in(client, officer_a, full_name="Ada").status_code == 422
    assert sign_in(client, officer_a, phone="").status_code == 422
    for missing in ("full_name", "phone", "signature"):  # a new phone has no signature on file
        body = payload()
        del body[missing]
        assert client.post(URL, json=body, headers=officer_a.headers).status_code == 422


def test_lookup_finds_a_returning_staff_member(client, officer_a, officer_b):
    def look(who, phone="+234 803 111 2222"):
        return client.get("/api/staff/lookup", params={"phone": phone}, headers=who.headers)

    assert look(officer_a).json() is None
    e = sign_in(client, officer_a, phone="08031112222", capacity="Cashier").json()
    found = look(officer_a).json()
    assert (found["full_name"], found["capacity"], found["phone"]) == (
        "Ada Okoro", "Cashier", "+2348031112222")
    assert found["open_entry_id"] == e["id"]
    assert look(officer_b).json() is None  # another facility has never seen them
    sign_out(client, officer_a, e["id"])
    assert look(officer_a).json()["open_entry_id"] is None


def test_one_sign_in_at_a_time(client, officer_a):
    first = sign_in(client, officer_a, phone="08031112222").json()
    again = sign_in(client, officer_a, phone="08031112222")
    assert again.status_code == 409 and again.json()["detail"]["code"] == "already_inside"
    sign_out(client, officer_a, first["id"])
    assert sign_in(client, officer_a, phone="08031112222").status_code == 201


def test_signatures_are_kept_and_reused(client, officer_a):
    phone = fresh_phone()
    eid = sign_in(client, officer_a, phone=phone).json()["id"]
    out = client.post(f"{URL}/{eid}/sign-out", json={}, headers=officer_a.headers)
    assert out.status_code == 200 and out.json()["has_signature_out"] is True  # sign-in one reused
    body = payload(phone=phone)
    del body["signature"]  # next day: no need to sign in again
    back = client.post(URL, json=body, headers=officer_a.headers)
    assert back.status_code == 201 and back.json()["has_signature"] is True
    fresh = payload()
    del fresh["signature"]  # a phone never seen here still has to sign
    assert client.post(URL, json=fresh, headers=officer_a.headers).status_code == 422
    seen = client.get("/api/staff/lookup", params={"phone": phone}, headers=officer_a.headers)
    assert seen.json()["has_signature"] is True


def test_search_finds_people_as_the_number_is_typed(client, officer_a, officer_b):
    def search(typed, who=officer_a):
        return client.get("/api/staff/search", params={"q": typed}, headers=who.headers)

    a = sign_in(client, officer_a, phone="08031112222", full_name="Ada Okoro").json()
    sign_out(client, officer_a, a["id"])
    sign_in(client, officer_a, phone="08039990000", full_name="Musa Bello")
    sign_in(client, officer_b, phone="08031113333", full_name="Other Place")

    assert search("080").status_code == 200
    assert [p["full_name"] for p in search("0803").json()] == ["Musa Bello", "Ada Okoro"]
    only = search("1112").json()  # the middle of a number matches too
    assert [(p["full_name"], p["phone"]) for p in only] == [("Ada Okoro", "+2348031112222")]
    assert only[0]["open_entry_id"] is None
    inside = search("0803999").json()
    assert [p["full_name"] for p in inside] == ["Musa Bello"] and inside[0]["open_entry_id"]
    assert search("+234 803 111").json()[0]["phone"] == "+2348031112222"
    assert search("0803111", officer_b).json()[0]["full_name"] == "Other Place"
    assert [p["full_name"] for p in search("0803111").json()] == ["Ada Okoro"]  # not theirs
    assert search("0555").json() == []


def test_search_lists_each_person_once_with_their_latest_details(client, officer_a):
    for who in ("Old Name", "New Name"):
        e = sign_in(client, officer_a, phone="08031112222", full_name=f"{who} Okoro").json()
        sign_out(client, officer_a, e["id"])
    found = client.get("/api/staff/search", params={"q": "0803111"},
                       headers=officer_a.headers).json()
    assert [p["full_name"] for p in found] == ["New Name Okoro"]


def test_search_needs_three_digits_and_a_facility(client, officer_a, cso):
    url = "/api/staff/search"
    assert client.get(url, params={"q": "08"}, headers=officer_a.headers).status_code == 422
    assert client.get(url, params={"q": "abc"}, headers=officer_a.headers).status_code == 422
    assert client.get(url, params={"q": "0803"}, headers=cso.headers).status_code == 403


def test_staff_numbers_are_real_numbers_for_their_country(client, officer_a):
    assert sign_in(client, officer_a, phone="+233 24 123 4567").json()["phone"] == "+233241234567"
    for bad in ("0803111222", "+999 123 456 789", "abc", 8031112222):
        assert sign_in(client, officer_a, phone=bad).status_code == 422, bad
