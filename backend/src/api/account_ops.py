

# backend/src/api/account_ops.py

"""Creating facility accounts through the API (used by admin_service).
Deliberately does NOT import security/accounts.py (CLI-only)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.src.db.orm._helpers import normalize_code
from backend.src.db.orm.tables import Counter, Facility, Officer
from backend.src.exceptions.errors import NotFoundError
from backend.src.models import ACCOUNT_CODE_PREFIX
from backend.src.security.passwords import generate_temp_pin, hash_pin


def _lock_active_facility(db: Session, facility_code: str) -> Facility:
    facility = db.scalar(
        select(Facility)
        .where(Facility.code == normalize_code(facility_code),
               Facility.is_active.is_(True))
        .with_for_update()
        .execution_options(populate_existing=True))
    if facility is None:
        raise NotFoundError("Facility not found.")
    return facility


def _locked_counter(db: Session, facility_id: uuid.UUID) -> Counter:
    name = f"officer_code:{facility_id}:{ACCOUNT_CODE_PREFIX}"
    db.execute(pg_insert(Counter).values(name=name, next_value=1)
               .on_conflict_do_nothing(index_elements=["name"]))
    row = db.scalar(
        select(Counter).where(Counter.name == name).with_for_update()
        .execution_options(populate_existing=True))
    assert row is not None
    return row


def _code_taken(db: Session, facility_id: uuid.UUID, code: str) -> bool:
    return db.scalar(select(Officer.id).where(
        Officer.officer_code == code, Officer.facility_id == facility_id)) is not None


def _next_code(db: Session, facility_id: uuid.UUID) -> str:
    """OFF-001, OFF-002 ... counted per facility. Skips codes that are taken
    (for example one an admin made by hand with the CLI)."""
    counter = _locked_counter(db, facility_id)
    while True:
        seq, counter.next_value = counter.next_value, counter.next_value + 1
        code = f"{ACCOUNT_CODE_PREFIX}-{seq:03d}"
        if not _code_taken(db, facility_id, code):
            return code


def create_account(
    db: Session, *, full_name: str, role: str, facility_code: str
) -> tuple[Officer, Facility, str]:
    """A non-admin account in an active facility, with an auto-issued code and a
    temp PIN. Returns (officer, facility, plain_temp_pin). Caller commits."""
    facility = _lock_active_facility(db, facility_code)
    pin = generate_temp_pin()
    officer = Officer(
        facility_id=facility.id,
        officer_code=_next_code(db, facility.id),
        full_name=full_name.strip(),
        pin_hash=hash_pin(pin),
        role=role,
        must_change_pin=True,
    )
    db.add(officer)
    db.flush()
    return officer, facility, pin
