

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

from backend.src.api.account_ops import create_account
from backend.src.db.orm._helpers import normalize_code
from backend.src.db.orm.tables import Facility, Officer
from backend.src.exceptions.errors import ConflictError, NotFoundError
from backend.src.models import DEFAULT_ROLE
from backend.src.security.passwords import generate_temp_pin, hash_pin
from backend.src.security.sessions import revoke_sessions as sign_out_everywhere

# ---- facilities ----


def create_facility(db: Session, *, code: str, name: str) -> Facility:
    facility = Facility(code=code, name=name.strip())  # code normalized by model
    db.add(facility)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            f"Facility {normalize_code(code)!r} already exists.") from None
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


def create_officer(
    db: Session, *, facility_code: str, full_name: str, role: str = DEFAULT_ROLE
) -> tuple[Officer, Facility, str]:
    """Returns (officer, facility, temp_pin). The temp PIN exists in plain text
    only in this return value."""
    officer, facility, pin = create_account(
        db, full_name=full_name, role=role, facility_code=facility_code)
    db.commit()
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


def reset_pin(db: Session, officer_id: uuid.UUID) -> tuple[Officer, str]:
    """New temp PIN, must_change_pin on, lockout cleared, every phone signed out."""
    officer = _managed_officer(db, officer_id)
    pin = generate_temp_pin()
    officer.pin_hash = hash_pin(pin)
    officer.must_change_pin = True
    officer.failed_pin_attempts = 0
    officer.locked_until = None
    sign_out_everywhere(db, officer.id)
    db.commit()
    return officer, pin


def set_officer_active(db: Session, officer_id: uuid.UUID, active: bool) -> None:
    officer = _managed_officer(db, officer_id)
    officer.is_active = active
    if not active:
        sign_out_everywhere(db, officer.id)
    db.commit()


def revoke_sessions(db: Session, officer_id: uuid.UUID) -> None:
    """Lost phone: sign the officer out everywhere, keep the account enabled."""
    officer = _managed_officer(db, officer_id)
    sign_out_everywhere(db, officer.id)
    db.commit()
