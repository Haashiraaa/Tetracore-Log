

# backend/src/api/admin_service.py

"""Admin operations. Same rule as auth_service: plain functions over a Session.

Admins manage every NON-admin account. Every officer lookup filters
is_admin = false, so an admin can never touch another admin: admins are set,
dropped and PIN-reset from the admin CLI only (scripts/admin_manager.py)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.src.api import event_service
from backend.src.api.account_ops import create_account
from backend.src.db.orm._helpers import normalize_code
from backend.src.db.orm.tables import Facility, Officer
from backend.src.db.queries.counters import take_number
from backend.src.exceptions.errors import ConflictError, NotFoundError
from backend.src.facility_codes import format_code, state_abbrev
from backend.src.models import DEFAULT_ROLE
from backend.src.security.passwords import generate_temp_pin, hash_pin
from backend.src.security.sessions import revoke_sessions as sign_out_everywhere

# ---- facilities ----


def _facility_code_taken(db: Session, code: str) -> bool:
    return db.scalar(select(Facility.id).where(Facility.code == code)) is not None


def create_facility(
    db: Session, *, actor_id: uuid.UUID, state: str, name: str
) -> Facility:
    """The server issues the code: CNG-<state>-<number>. `state` is already a
    canonical state name (the request schema checks it). The number comes from a
    per-state counter that only goes up, and skips a code that is already taken
    (for example one seeded by hand)."""
    counter_name = f"facility_code:{state_abbrev(state)}"
    while True:
        code = format_code(state, take_number(db, counter_name))
        if not _facility_code_taken(db, code):
            break
    facility = Facility(code=code, state=state, name=name.strip())
    db.add(facility)
    try:
        db.flush()
        event = event_service.record(
            db, kind="facility_added", facility_id=facility.id, actor_id=actor_id,
            summary=f"Facility {facility.code} ({facility.name}) was added.")
        db.commit()
    except IntegrityError:  # a parallel request took the same name: let it retry
        db.rollback()
        raise ConflictError("Could not issue a facility code. Try again.") from None
    event_service.announce(event.id)
    return facility


def list_facilities(db: Session) -> list[Facility]:
    return list(db.scalars(select(Facility).order_by(Facility.code)))


# ---- officers ----


def _managed_officer(db: Session, officer_id: uuid.UUID) -> Officer:
    """Row-locked non-admin account, or NotFound. Admins are invisible here."""
    officer = db.scalar(
        select(Officer)
        .where(Officer.id == officer_id, Officer.is_admin.is_(False))
        .with_for_update()
    )
    if officer is None:
        raise NotFoundError("Officer not found.")
    return officer


def _record(db: Session, kind: str, officer: Officer, actor_id: uuid.UUID, summary: str):
    return event_service.record(
        db, kind=kind, summary=summary, facility_id=officer.facility_id, actor_id=actor_id)


def create_officer(
    db: Session, *, actor_id: uuid.UUID, facility_code: str, full_name: str,
    role: str = DEFAULT_ROLE,
) -> tuple[Officer, Facility, str]:
    """Returns (officer, facility, temp_pin). The temp PIN exists in plain text
    only in this return value."""
    officer, facility, pin = create_account(
        db, full_name=full_name, role=role, facility_code=facility_code)
    event = _record(db, "officer_added", officer, actor_id,
                    f"{officer.full_name} ({officer.officer_code}) was added to {facility.code}.")
    db.commit()
    event_service.announce(event.id)
    return officer, facility, pin


def list_officers(
    db: Session, facility_code: str | None = None
) -> list[tuple[Officer, Facility | None]]:
    stmt = (
        select(Officer, Facility)
        .outerjoin(Facility, Facility.id == Officer.facility_id)
        .where(Officer.is_admin.is_(False))
        .order_by(Facility.code, Officer.officer_code)
    )
    if facility_code:
        stmt = stmt.where(Facility.code == normalize_code(facility_code))
    return [(o, f) for o, f in db.execute(stmt).all()]


def reset_pin(
    db: Session, officer_id: uuid.UUID, *, actor_id: uuid.UUID
) -> tuple[Officer, str]:
    """New temp PIN, must_change_pin on, lockout cleared, every phone signed out."""
    officer = _managed_officer(db, officer_id)
    pin = generate_temp_pin()
    officer.pin_hash = hash_pin(pin)
    officer.must_change_pin = True
    officer.failed_pin_attempts = 0
    officer.locked_until = None
    sign_out_everywhere(db, officer.id)
    event = _record(db, "officer_pin_reset", officer, actor_id,
                    f"PIN reset for {officer.full_name} ({officer.officer_code}).")
    db.commit()
    event_service.announce(event.id)
    return officer, pin


def set_officer_active(
    db: Session, officer_id: uuid.UUID, active: bool, *, actor_id: uuid.UUID
) -> None:
    officer = _managed_officer(db, officer_id)
    officer.is_active = active
    if not active:
        sign_out_everywhere(db, officer.id)
    event = _record(
        db, "officer_enabled" if active else "officer_disabled", officer, actor_id,
        f"{officer.full_name} ({officer.officer_code}) was "
        f"{'enabled' if active else 'disabled'}.")
    db.commit()
    event_service.announce(event.id)


def revoke_sessions(db: Session, officer_id: uuid.UUID, *, actor_id: uuid.UUID) -> None:
    """Lost phone: sign the officer out everywhere, keep the account enabled."""
    officer = _managed_officer(db, officer_id)
    sign_out_everywhere(db, officer.id)
    event = _record(db, "sessions_revoked", officer, actor_id,
                    f"{officer.full_name} ({officer.officer_code}) was signed out everywhere.")
    db.commit()
    event_service.announce(event.id)
