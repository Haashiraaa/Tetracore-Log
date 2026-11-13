# tests/api/routes/test_input_types.py

"""A field that wants an integer is not given one by a string, a float or a flag, and so on:
the API refuses the wrong type instead of quietly converting it."""

import base64
import uuid

import pytest

PNG_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64).decode()

NOT_AN_INTEGER = ["1", "1.0", 1.0, 1.5, True, None, [1], {"n": 1}]


def go_on(client, who, gate):
    return client.post("/api/duty/on", json={"id": str(uuid.uuid4()), "gate": gate},
                       headers=who.headers)


def truck(**over):
    return {"id": str(uuid.uuid4()), "plate_number": "typ-111 aa", "driver_name": "Musa Ibrahim",
            **over}


@pytest.mark.parametrize("bad", NOT_AN_INTEGER)
def test_a_gate_must_be_an_integer(client, officer_a, bad):
    r = go_on(client, officer_a, bad)
    assert r.status_code == 422, r.text


def test_a_gate_that_is_an_integer_is_not_a_type_error(client, officer_a):
    assert go_on(client, officer_a, 1).status_code != 422  # (409 if already on duty)


@pytest.mark.parametrize("bad", NOT_AN_INTEGER)
def test_a_gate_count_must_be_an_integer(client, admin, officer_a, bad):
    r = client.put(f"/api/admin/facilities/{officer_a.facility}/gates",
                   json={"gate_count": bad}, headers=admin.headers)
    assert r.status_code == 422, r.text
    made = client.post("/api/admin/facilities", json={"state": "Lagos", "name": "Typed Test",
                                                      "gate_count": bad}, headers=admin.headers)
    assert made.status_code == 422, made.text


@pytest.mark.parametrize("bad", ["true", "false", "yes", 1, 0, "1", None, []])
def test_enter_now_must_be_a_real_boolean(client, officer_a, bad):
    r = client.post("/api/trucks/entries", json=truck(enter_now=bad), headers=officer_a.headers)
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("bad", [True, False, "abc", "NaN", "Infinity", "-1", [1], {"a": 1}])
def test_gas_bought_must_be_a_number(client, officer_a, bad):
    queued = client.post("/api/trucks/entries", json=truck(), headers=officer_a.headers)
    assert queued.status_code == 201, queued.text
    entry = queued.json()
    client.post(f"/api/trucks/entries/{entry['id']}/enter", json={"signature": PNG_B64},
                headers=officer_a.headers)
    r = client.post(f"/api/trucks/entries/{entry['id']}/sign-out",
                    json={"signature": PNG_B64, "scm_purchased": bad}, headers=officer_a.headers)
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("good", ["12.50", 12.5, 12, "0"])
def test_gas_bought_accepts_a_decimal_string_or_a_number(client, officer_a, good):
    r = client.post("/api/trucks/entries",
                    json=truck(plate_number=f"gas-{uuid.uuid4().hex[:6]}", enter_now=True,
                               signature=PNG_B64, scm_purchased=good),
                    headers=officer_a.headers)
    assert r.status_code == 201, r.text


@pytest.mark.parametrize("field,bad", [("full_name", 123), ("full_name", ["Ada Okoro"]),
                                       ("company", 5), ("purpose", True), ("phone", 8031112222),
                                       ("signature", 7)])
def test_text_fields_do_not_take_other_types(client, officer_a, field, bad):
    body = {"id": str(uuid.uuid4()), "full_name": "Ada Okoro", "phone": "08031112222",
            "signature": PNG_B64, field: bad}
    r = client.post("/api/visitors/entries", json=body, headers=officer_a.headers)
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("bad", ["abc", 5, True, {}, [[]], None])
def test_items_must_be_a_list_of_name_and_quantity(client, officer_a, bad):
    body = {"id": str(uuid.uuid4()), "full_name": "Ada Okoro", "phone": "08031112222",
            "signature": PNG_B64, "items": bad}
    assert client.post("/api/visitors/entries", json=body,
                       headers=officer_a.headers).status_code == 422


@pytest.mark.parametrize("bad", [1, 12, True, ["a"], None])
def test_an_item_name_and_unit_are_text(client, officer_a, bad):
    for item in ({"name": bad, "quantity": 1}, {"name": "Gloves", "quantity": 1, "unit": bad}):
        if item.get("unit") is None and "unit" in item:
            continue  # null unit means "no unit" and is fine
        body = {"id": str(uuid.uuid4()), "full_name": "Ada Okoro", "phone": "08031112222",
                "signature": PNG_B64, "items": [item]}
        assert client.post("/api/visitors/entries", json=body,
                           headers=officer_a.headers).status_code == 422


@pytest.mark.parametrize("bad", ["2", "2 boxes", "", 2.5, True, False, 0, -1, 100_001, None, [2]])
def test_an_item_quantity_must_be_a_whole_number(client, officer_a, bad):
    body = {"id": str(uuid.uuid4()), "full_name": "Ada Okoro", "phone": "08031112222",
            "signature": PNG_B64, "items": [{"name": "Gloves", "quantity": bad}]}
    assert client.post("/api/visitors/entries", json=body,
                       headers=officer_a.headers).status_code == 422


def test_an_item_quantity_and_unit_are_kept(client, officer_a):
    body = {"id": str(uuid.uuid4()), "full_name": "Ada Okoro", "phone": "08031112222",
            "signature": PNG_B64,
            "items": [{"name": "Water", "quantity": 3, "unit": "cartons"},
                      {"name": "Gloves", "quantity": 100_000, "unit": ""}]}
    r = client.post("/api/visitors/entries", json=body, headers=officer_a.headers)
    assert r.status_code == 201, r.text
    assert r.json()["items"] == [{"name": "Water", "quantity": 3, "unit": "cartons"},
                                 {"name": "Gloves", "quantity": 100000, "unit": None}]
