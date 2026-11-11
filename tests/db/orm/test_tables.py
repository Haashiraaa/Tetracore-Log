
# tests/db/orm/test_tables.py  (backend/src/db/orm/tables.py)

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.src.db.orm.tables import Officer
from backend.src.db.session import create_session
from tests._helpers import make_account


def officer(**over) -> Officer:
    return Officer(officer_code="x-1", full_name="X", pin_hash="h", **over)


def test_role_label_is_trimmed_and_blank_is_refused():
    assert officer(role="  Shift Lead ").role == "Shift Lead"
    with pytest.raises(ValueError):
        officer(role="   ")


def test_the_database_refuses_a_blank_role_too():
    """Even a raw UPDATE that skips the ORM validator."""
    make_account(code="OFF-001", facility="CNG-A")
    with create_session() as db, pytest.raises(IntegrityError):
        db.execute(text("UPDATE officers SET role = '   '"))
        db.commit()


def test_scope_properties_follow_facility_and_admin_not_role():
    facility = uuid.uuid4()
    member = officer(role="cso", facility_id=facility, is_admin=False)
    assert (member.can_write_entries, member.sees_all_facilities) == (True, False)
    global_viewer = officer(role="officer", facility_id=None, is_admin=False)
    assert (global_viewer.can_write_entries, global_viewer.sees_all_facilities) == (False, True)
    admin = officer(role="officer", facility_id=facility, is_admin=True)
    assert (admin.can_write_entries, admin.sees_all_facilities) == (True, True)
