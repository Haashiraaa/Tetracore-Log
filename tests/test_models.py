
# tests/test_models.py  (backend/src/models.py)

import uuid

import pytest

from backend.src.models import (
    ROLE_MAX_LENGTH,
    clean_role,
    may_write_entries,
    sees_every_facility,
)

FACILITY = uuid.uuid4()


@pytest.mark.parametrize("raw, expected", [
    ("officer", "officer"),
    ("  Facility Manager ", "Facility Manager"),
    ("cso", "cso"),                       # no label is special
    ("x" * ROLE_MAX_LENGTH, "x" * ROLE_MAX_LENGTH),
])
def test_clean_role_accepts_any_label(raw, expected):
    assert clean_role(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "x" * (ROLE_MAX_LENGTH + 1)])
def test_clean_role_rejects_blank_and_overlong(raw):
    with pytest.raises(ValueError):
        clean_role(raw)


@pytest.mark.parametrize("is_admin, facility_id, expected", [
    (False, FACILITY, False),   # a facility member sees only its facility
    (False, None, True),        # a global account sees all
    (True, FACILITY, True),     # an admin sees all
    (True, None, True),
])
def test_sees_every_facility(is_admin, facility_id, expected):
    assert sees_every_facility(is_admin=is_admin, facility_id=facility_id) is expected


def test_only_facility_members_write_entries():
    assert may_write_entries(facility_id=FACILITY) is True
    assert may_write_entries(facility_id=None) is False
