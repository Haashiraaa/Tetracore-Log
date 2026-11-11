# tests/security/test_sessions.py

from datetime import timedelta

import pytest
from sqlalchemy import select

from backend.src.db.orm.tables import Facility, Officer, OfficerSession
from backend.src.db.session import create_session
from backend.src.exceptions.errors import SessionRevokedError
from backend.src.security.sessions import (
    assert_session_usable,
    load_session_row,
    revoke_sessions,
)
from backend.src.security.tokens import utcnow
from tests._helpers import login, make_account


def _sessions(db, officer_id):
    return list(db.scalars(select(OfficerSession).where(OfficerSession.officer_id == officer_id)))


def _row(db, officer_id):
    row = load_session_row(db, OfficerSession.officer_id == officer_id)
    assert row is not None
    return row


def test_revoke_sessions_can_keep_the_phone_in_hand(client):
    oid = make_account(code="OFF-001", facility="CNG-A")
    login(client, "OFF-001", "CNG-A")
    login(client, "OFF-001", "CNG-A")
    with create_session() as db:
        keep = _sessions(db, oid)[0].id
        revoke_sessions(db, oid, keep=keep)
        db.commit()
        live = [s.id for s in _sessions(db, oid) if s.revoked_at is None]
        assert live == [keep]
        revoke_sessions(db, oid)
        db.commit()
        assert all(s.revoked_at is not None for s in _sessions(db, oid))


def test_load_session_row_reports_facility_state(client):
    oid = make_account(code="OFF-001", facility="CNG-A")
    gid = make_account(code="G-1")
    login(client, "OFF-001", "CNG-A")
    login(client, "G-1")
    with create_session() as db:
        assert _row(db, oid)[2] is True
        assert _row(db, gid)[2] is None  # a global account has no facility
        assert load_session_row(db, OfficerSession.officer_id == oid, lock=True) is not None


def test_usable_session_passes_and_each_failure_is_refused(client):
    oid = make_account(code="OFF-001", facility="CNG-A")
    login(client, "OFF-001", "CNG-A")
    now = utcnow()
    with create_session() as db:
        assert_session_usable(_row(db, oid), now)

        with pytest.raises(SessionRevokedError):  # expired
            assert_session_usable(_row(db, oid), now + timedelta(days=3650))

        officer = db.get(Officer, oid)
        assert officer is not None
        officer.is_active = False
        db.flush()
        with pytest.raises(SessionRevokedError, match="account"):
            assert_session_usable(_row(db, oid), now)
        officer.is_active = True

        facility = db.scalar(select(Facility))
        assert facility is not None
        facility.is_active = False
        db.flush()
        with pytest.raises(SessionRevokedError, match="facility"):
            assert_session_usable(_row(db, oid), now)
        db.rollback()


def test_revoked_session_is_refused(client):
    oid = make_account(code="OFF-001", facility="CNG-A")
    login(client, "OFF-001", "CNG-A")
    with create_session() as db:
        revoke_sessions(db, oid)
        db.flush()
        with pytest.raises(SessionRevokedError):
            assert_session_usable(_row(db, oid), utcnow())
        db.rollback()
