

# backend/src/security/accounts.py

"""Account operations for seed scripts / CLI ONLY.

Nothing in the API imports this module. That is how is_admin stays unreachable
from a request body: admins are set and dropped here and nowhere else.
Every function raises ValueError on bad input. The caller commits.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.src.db.orm._helpers import normalize_code
from backend.src.db.orm.tables import Facility, Officer
from backend.src.models import DEFAULT_ROLE, clean_full_name
from backend.src.security.passwords import hash_pin, validate_pin_policy
from backend.src.security.sessions import revoke_sessions


def get_or_create_facility(db: Session, code: str, name: str) -> tuple[Facility, bool]:
    code = normalize_code(code)
    facility = db.scalar(select(Facility).where(Facility.code == code))
    if facility is not None:
        return facility, False
    facility = Facility(code=code, name=name)
    db.add(facility)
    db.flush()
    return facility, True


def find_officer(
    db: Session, *, officer_code: str, facility_code: str | None = None
) -> Officer:
    """Lookup by the same (facility, officer code) pair used at login."""
    stmt = select(Officer).where(
        Officer.officer_code == normalize_code(officer_code))
    if facility_code:
        stmt = stmt.join(Facility, Facility.id == Officer.facility_id).where(
            Facility.code == normalize_code(facility_code))
    else:
        stmt = stmt.where(Officer.facility_id.is_(None))
    officer = db.scalar(stmt.with_for_update(of=Officer))
    if officer is None:
        raise ValueError("No such officer for that facility/code.")
    return officer


def _facility_id_for(db: Session, facility_code: str | None) -> uuid.UUID | None:
    """None in, None out: a global account has no facility."""
    if facility_code is None:
        return None
    facility = db.scalar(select(Facility).where(
        Facility.code == normalize_code(facility_code)))
    if facility is None:
        raise ValueError(f"Facility {facility_code!r} does not exist.")
    return facility.id


def _assert_code_free(
    db: Session, officer_code: str, facility_id: uuid.UUID | None
) -> None:
    same_scope = (Officer.facility_id == facility_id if facility_id is not None
                  else Officer.facility_id.is_(None))
    taken = db.scalar(select(Officer.id).where(
        Officer.officer_code == officer_code, same_scope))
    if taken is not None:
        raise ValueError(f"Officer code {officer_code!r} already exists there.")


def create_officer(
    db: Session,
    *,
    officer_code: str,
    full_name: str,
    pin: str,
    role: str = DEFAULT_ROLE,
    is_admin: bool = False,
    facility_code: str | None = None,
) -> Officer:
    """No facility_code means a global account."""
    validate_pin_policy(pin)
    facility_id = _facility_id_for(db, facility_code)
    code = normalize_code(officer_code)
    _assert_code_free(db, code, facility_id)
    officer = Officer(
        facility_id=facility_id, officer_code=code, full_name=clean_full_name(full_name),
        pin_hash=hash_pin(pin), role=role, is_admin=is_admin)
    db.add(officer)
    db.flush()
    return officer


# ---- admins: the only place they are set, dropped or PIN-reset ----


def count_active_admins(db: Session) -> int:
    db.flush()  # sessions run with autoflush off: count what this transaction changed too
    return db.scalar(select(func.count()).select_from(Officer).where(
        Officer.is_admin.is_(True), Officer.is_active.is_(True))) or 0


def grant_admin(officer: Officer) -> None:
    if officer.is_admin:
        raise ValueError("That account is already an admin.")
    if not officer.is_active:
        raise ValueError("That account is disabled. Enable it first.")
    officer.is_admin = True


def revoke_admin(db: Session, officer: Officer, *, force: bool = False) -> None:
    """The account keeps its role, facility and code; it just loses admin powers
    from its next request (deps re-reads the DB every time)."""
    if not officer.is_admin:
        raise ValueError("That account is not an admin.")
    last = officer.is_active and count_active_admins(db) <= 1
    if last and not force:
        raise ValueError(
            "This is the LAST active admin. Create or grant another first, "
            "or pass --force if you really mean it.")
    officer.is_admin = False


def reset_admin_pin(db: Session, officer: Officer, pin: str) -> None:
    """Set the PIN an admin chose at the console and sign them out everywhere."""
    if not officer.is_admin:
        raise ValueError("CLI PIN reset is for admins only. "
                         "Other accounts are reset from the admin page.")
    validate_pin_policy(pin)
    officer.pin_hash = hash_pin(pin)
    officer.must_change_pin = False
    officer.failed_pin_attempts = 0
    officer.locked_until = None
    revoke_sessions(db, officer.id)
