# tests/test_facility_codes.py  (backend/src/facility_codes.py)

from backend.src.facility_codes import (
    CODE_RE,
    FCT,
    STATES,
    canonical_state,
    format_code,
    state_abbrev,
)


def test_every_state_has_its_own_three_letters():
    abbrevs = [state_abbrev(s) for s in STATES]
    assert len(STATES) == 37 and len(set(abbrevs)) == 37
    assert all(len(a) == 3 and a.isalpha() for a in abbrevs)


def test_abbreviations():
    assert state_abbrev("Lagos") == "LAG"
    assert state_abbrev("Akwa Ibom") == "AKW"
    assert state_abbrev(FCT) == "FCT"


def test_format_and_pattern():
    assert format_code("Lagos", 1) == "CNG-LAG-01"
    assert format_code("Lagos", 100) == "CNG-LAG-100"
    assert all(CODE_RE.match(format_code(s, 7)) for s in STATES)
    assert not CODE_RE.match("CNG-N") and not CODE_RE.match("CNG-LAG-1")


def test_canonical_state_forgives_case_and_spacing_only():
    assert canonical_state("  cross   RIVER ") == "Cross River"
    assert canonical_state("Lag") is None
