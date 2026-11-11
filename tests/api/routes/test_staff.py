# tests/api/routes/test_staff.py

"""The staff log is a space for now: reading works, scoped like every log."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from backend.src.db.orm.tables import Facility, Staff, StaffEntry
from backend.src.db.session import create_session


def add_staff_entry(who) -> uuid.UUID:
    with create_session() as db:
        fid = db.scalar(select(Facility.id).where(Facility.code == who.facility))
        member = Staff(facility_id=fid, staff_code="s-1", full_name="Staff One")
        db.add(member)
        db.flush()
        entry = StaffEntry(
            facility_id=fid, staff_id=member.id, signed_in_by=who.id,
            signed_in_at=datetime(2026, 11, 1, tzinfo=timezone.utc))
        db.add(entry)
        db.commit()
        return entry.id


def test_requires_login(client):
    assert client.get("/api/staff/entries").status_code == 401


def test_each_facility_sees_only_its_own(client, officer_a, officer_b):
    mine = add_staff_entry(officer_a)
    add_staff_entry(officer_b)
    r = client.get("/api/staff/entries", headers=officer_a.headers)
    assert [e["id"] for e in r.json()] == [str(mine)]
    assert "staff_id" in r.json()[0]


def test_admin_sees_every_facility(client, officer_a, officer_b, admin):
    add_staff_entry(officer_a)
    add_staff_entry(officer_b)
    assert len(client.get("/api/staff/entries", headers=admin.headers).json()) == 2
