
# tests/test_models.py  (backend/src/models.py)

import uuid

import pytest

from backend.src.models import (
    DEFAULT_ROLE,
    ROLE_MAX_LENGTH,
    clean_full_name,
    clean_phone,
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


def test_the_default_role_has_a_capital_o():
    assert DEFAULT_ROLE == "Officer"


@pytest.mark.parametrize("raw, expected", [
    ("Ada Okoro", "Ada Okoro"),
    ("  ada   okoro ", "ada okoro"),
    ("Chukwuemeka Obi Nwosu", "Chukwuemeka Obi Nwosu"),
])
def test_clean_full_name(raw, expected):
    assert clean_full_name(raw) == expected


@pytest.mark.parametrize("raw", ["", "  ", "Ada", "  Ada  "])
def test_a_single_name_is_not_a_full_name(raw):
    with pytest.raises(ValueError):
        clean_full_name(raw)


@pytest.mark.parametrize("raw, expected", [
    ("08031112222", "08031112222"),
    ("0803 111 2222", "08031112222"),
    ("0803-111-2222", "08031112222"),
    ("+234 803 111 2222", "08031112222"),
    ("2348031112222", "08031112222"),
    ("(0803) 111 2222", "08031112222"),
])
def test_clean_phone_gives_one_form(raw, expected):
    assert clean_phone(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "12345", "1" * 16])
def test_clean_phone_rejects_non_numbers(raw):
    with pytest.raises(ValueError):
        clean_phone(raw)
