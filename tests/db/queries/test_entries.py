# tests/db/queries/test_entries.py

"""The SQL every log shares, exercised through the visitor log (the simplest one)."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from backend.src.db.orm.tables import Facility, VisitorEntry
from backend.src.db.queries import _entries
from backend.src.db.session import create_session
from tests._helpers import make_actor

T0 = datetime(2026, 11, 1, 8, 0, tzinfo=timezone.utc)


def _facility_id(db, code: str) -> uuid.UUID:
    return db.scalar(select(Facility.id).where(Facility.code == code))


def _add(db, who, *, hours: int = 0, entry_id=None, signature=None) -> uuid.UUID:
    entry_id = entry_id or uuid.uuid4()
    _entries.insert_entry(
        db, VisitorEntry, id=entry_id, facility_id=_facility_id(db, who.facility),
        full_name="Visitor", signed_in_at=T0 + timedelta(hours=hours),
        signed_in_by=who.id, signature_in=signature)
    db.commit()
    return entry_id


def test_insert_is_idempotent(client):
    who = make_actor(client, code="OFF-001", facility="CNG-A")
    with create_session() as db:
        eid = _add(db, who)
        again = _entries.insert_entry(
            db, VisitorEntry, id=eid, facility_id=_facility_id(db, "CNG-A"),
            full_name="Someone else", signed_in_at=T0, signed_in_by=who.id)
        assert again is False
        row = _entries.get_entry(db, VisitorEntry, eid, None)
        assert row is not None and row[0].full_name == "Visitor"


def test_list_is_newest_first_and_honours_scope(client):
    a = make_actor(client, code="OFF-001", facility="CNG-A")
    b = make_actor(client, code="OFF-001", facility="CNG-B")
    with create_session() as db:
        old, new = _add(db, a, hours=0), _add(db, a, hours=5)
        _add(db, b, hours=9)
        scoped = _entries.list_entries(db, VisitorEntry, scope=_facility_id(db, "CNG-A"))
        assert [r[0].id for r in scoped] == [new, old]
        everything = _entries.list_entries(db, VisitorEntry, scope=None)
        assert len(everything) == 3
        only_b = _entries.list_entries(db, VisitorEntry, scope=None, facility_code="cng-b")
        assert len(only_b) == 1


def test_facility_code_is_ignored_when_scoped(client):
    a = make_actor(client, code="OFF-001", facility="CNG-A")
    make_actor(client, code="OFF-002", facility="CNG-B")
    with create_session() as db:
        _add(db, a)
        rows = _entries.list_entries(
            db, VisitorEntry, scope=_facility_id(db, "CNG-A"), facility_code="CNG-B")
        assert len(rows) == 1


def test_open_and_date_filters(client):
    who = make_actor(client, code="OFF-001", facility="CNG-A")
    with create_session() as db:
        early, late = _add(db, who, hours=0), _add(db, who, hours=10)
        _entries.sign_out_entry(
            db, VisitorEntry, entry_id=early, facility_id=_facility_id(db, "CNG-A"),
            officer_id=who.id, signed_out_at=T0 + timedelta(hours=1))
        db.commit()
        still_open = _entries.list_entries(db, VisitorEntry, open_only=True, scope=None)
        assert [r[0].id for r in still_open] == [late]
        cut = T0 + timedelta(hours=5)
        after = _entries.list_entries(db, VisitorEntry, date_from=cut, scope=None)
        assert [r[0].id for r in after] == [late]
        end = T0 + timedelta(hours=10)
        before = _entries.list_entries(db, VisitorEntry, date_to=end, scope=None)
        assert [r[0].id for r in before] == [early]  # date_to is exclusive


def _close(db, who, eid, fid, hours):
    return _entries.sign_out_entry(
        db, VisitorEntry, entry_id=eid, facility_id=fid, officer_id=who.id,
        signed_out_at=T0 + timedelta(hours=hours))


def _get(db, eid, scope):
    row = _entries.get_entry(db, VisitorEntry, eid, scope)
    assert row is not None
    return row


def test_first_sign_out_wins_and_is_facility_bound(client):
    who = make_actor(client, code="OFF-001", facility="CNG-A")
    with create_session() as db:
        fid, eid = _facility_id(db, "CNG-A"), _add(db, who)
        assert _close(db, who, eid, uuid.uuid4(), 0) is False
        assert _close(db, who, eid, fid, 1) is True
        assert _close(db, who, eid, fid, 2) is False
        db.expire_all()
        row = _get(db, eid, fid)
        assert row[0].signed_out_at == T0 + timedelta(hours=1)
        assert row[4] == "Test OFF-001"


def test_signature_is_only_visible_in_scope(client):
    who = make_actor(client, code="OFF-001", facility="CNG-A")
    with create_session() as db:
        eid = _add(db, who, signature=b"png-bytes")
        fid = _facility_id(db, "CNG-A")
        mine = _entries.get_signature(db, VisitorEntry, eid, fid)
        assert mine is not None and mine[0] == b"png-bytes"
        assert _entries.get_signature(db, VisitorEntry, eid, uuid.uuid4()) is None
        assert _get(db, eid, None)[2] is True  # has_signature, without loading the blob
