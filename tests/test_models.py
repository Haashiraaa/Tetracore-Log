
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
    phone_search_digits,
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
    ("08031112222", "+2348031112222"),
    ("0803 111 2222", "+2348031112222"),
    ("0803-111-2222", "+2348031112222"),
    ("+234 803 111 2222", "+2348031112222"),
    ("2348031112222", "+2348031112222"),
    ("(0803) 111 2222", "+2348031112222"),
    ("8031112222", "+2348031112222"),
    ("+44 7911 123456", "+447911123456"),      # UK mobile
    ("+233 24 123 4567", "+233241234567"),     # Ghana
    ("+1 202 555 0143", "+12025550143"),       # USA
])
def test_clean_phone_gives_one_form(raw, expected):
    assert clean_phone(raw) == expected


@pytest.mark.parametrize("raw", [
    "", "  ", "abc", "12345", "1" * 16,
    "0803111222",            # one digit short for a Nigerian number
    "080311122223",          # one too many
    "07700 900123",          # 0770 is not a Nigerian mobile prefix
    "+44 7911 12345",        # one digit short for the UK
    "+999 123 456 789",      # no such country
    "08031112222 ext 5",     # extensions and letters are not numbers
    "1-800-FLOWERS",
])
def test_clean_phone_rejects_numbers_that_are_not_real(raw):
    with pytest.raises(ValueError):
        clean_phone(raw)


def test_the_error_says_how_to_write_a_number():
    with pytest.raises(ValueError, match=r"0803 123 4567.*\+44"):
        clean_phone("nope")


@pytest.mark.parametrize("raw,expected", [
    ("080", "80"), ("0803-111", "803111"), ("+234 803 11", "23480311"), ("234803", "234803"),
    ("803", "803"), ("0044 7911", "447911"), ("+44 79", "4479"),
])
def test_phone_search_digits_is_the_number_so_far(raw, expected):
    assert phone_search_digits(raw) == expected


@pytest.mark.parametrize("raw", ["", "08", "ab", "+2"])
def test_phone_search_digits_needs_three_digits(raw):
    with pytest.raises(ValueError):
        phone_search_digits(raw)
