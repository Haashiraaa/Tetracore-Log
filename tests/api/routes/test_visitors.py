# tests/api/routes/test_visitors.py

"""The visitor log is a space for now: reading works, scoped like every log."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from backend.src.db.orm.tables import Facility, VisitorEntry
from backend.src.db.session import create_session


def add_visitor(who) -> uuid.UUID:
    eid = uuid.uuid4()
    with create_session() as db:
        db.add(VisitorEntry(
            id=eid, facility_id=db.scalar(select(Facility.id).where(Facility.code == who.facility)),
            full_name="V", signed_in_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
            signed_in_by=who.id, signature_in=b"png"))
        db.commit()
    return eid


def test_requires_login(client):
    assert client.get("/api/visitors/entries").status_code == 401


def test_each_facility_sees_only_its_own(client, officer_a, officer_b):
    mine = add_visitor(officer_a)
    add_visitor(officer_b)
    r = client.get("/api/visitors/entries", headers=officer_a.headers)
    assert r.status_code == 200
    assert [e["id"] for e in r.json()] == [str(mine)]
    assert r.json()[0]["has_signature"] is True


def test_admin_and_global_accounts_see_every_facility(client, officer_a, officer_b, admin, cso):
    add_visitor(officer_a)
    add_visitor(officer_b)
    for who in (admin, cso):
        r = client.get("/api/visitors/entries", headers=who.headers)
        assert len(r.json()) == 2


def test_signature_download_is_scoped(client, officer_a, officer_b):
    eid = add_visitor(officer_a)
    url = f"/api/visitors/entries/{eid}/signature"
    ok = client.get(url, headers=officer_a.headers)
    assert ok.status_code == 200 and ok.headers["content-type"] == "image/png"
    assert client.get(url, headers=officer_b.headers).status_code == 404


def test_list_paging_is_validated(client, officer_a):
    assert client.get("/api/visitors/entries?limit=0", headers=officer_a.headers).status_code == 422
