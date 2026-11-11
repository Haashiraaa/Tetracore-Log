

# backend/src/api/auth_service.py

"""Login / refresh / logout logic. Plain functions over a Session so they are
testable without FastAPI. Routes stay thin.

Session policy (deliberate, for an OFFLINE-FIRST app):
* Refresh tokens are NOT rotated. Rotation means a lost HTTP response (very
  common on a gate-house mobile connection) leaves the phone holding a dead
  token and the guard locked out mid-shift with a queue of unsynced entries.
  Instead the refresh token is long-lived, hashed at rest, revocable per
  session, and its expiry slides forward each time it is used.
* The access token is short-lived; every request re-checks the session and
  officer in the DB (see api/deps.py), so revocation is immediate.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from backend.src.api.schemas import LoginResult, RefreshResult
from backend.src.config.settings import Settings
from backend.src.db.orm._helpers import normalize_code
from backend.src.db.orm.tables import Facility, Officer, OfficerSession
from backend.src.exceptions.errors import (
    AccountLockedError,
    InvalidCredentialsError,
    InvalidTokenError,
    SessionRevokedError,
    WeakPinError,
)
from backend.src.security.passwords import (
    burn_verify_time,
    hash_pin,
    needs_rehash,
    validate_pin_policy,
    verify_pin,
)
from backend.src.security.sessions import (
    assert_session_usable,
    load_session_row,
    revoke_sessions,
)
from backend.src.security.tokens import (
    create_access_token,
    hash_refresh_token,
    new_refresh_token,
    utcnow,
)

# ---- PIN checks, shared by login and change-PIN ---------------------------


def _assert_not_locked(officer: Officer, now: datetime) -> None:
    if officer.locked_until is not None and officer.locked_until > now:
        raise AccountLockedError(
            int((officer.locked_until - now).total_seconds()) + 1)


def _register_failed_pin(db: Session, officer: Officer, now: datetime) -> None:
    """Count a wrong PIN and lock the account at the limit. Commits first so
    the counter survives the exception the caller raises next."""
    officer.failed_pin_attempts += 1
    if officer.failed_pin_attempts >= Settings.MAX_PIN_ATTEMPTS:
        officer.locked_until = now + timedelta(minutes=Settings.LOCKOUT_MINUTES)
        officer.failed_pin_attempts = 0
        db.commit()
        raise AccountLockedError(Settings.LOCKOUT_MINUTES * 60)
    db.commit()


def _check_pin(
    db: Session, officer: Officer, pin: str, now: datetime, *, message: str | None = None
) -> None:
    """Raise unless `pin` is right. Counts the miss and may lock the account."""
    _assert_not_locked(officer, now)
    if not verify_pin(pin, officer.pin_hash):
        _register_failed_pin(db, officer, now)  # raises if it locks
        raise InvalidCredentialsError(message) if message else InvalidCredentialsError()


def _clear_pin_failures(officer: Officer) -> None:
    officer.failed_pin_attempts = 0
    officer.locked_until = None


# ---- login ----------------------------------------------------------------


def _login_query(facility_code: str | None, officer_code: str) -> Select[tuple[Officer]]:
    stmt = select(Officer).where(Officer.officer_code == normalize_code(officer_code))
    if facility_code is None or not facility_code.strip():
        return stmt.where(Officer.facility_id.is_(None))
    # The (facility, officer) PAIR must match: a right officer code with the
    # wrong facility finds nothing and fails exactly like a wrong PIN.
    return stmt.join(Facility, Facility.id == Officer.facility_id).where(
        Facility.code == normalize_code(facility_code),
        Facility.is_active.is_(True),
    )


def _find_login_officer(
    db: Session, facility_code: str | None, officer_code: str, pin: str
) -> Officer:
    # Row lock so two parallel wrong-PIN requests can't both read attempts=4
    # and slip past the lockout counter.
    stmt = _login_query(facility_code, officer_code).with_for_update(of=Officer)
    officer = db.scalar(stmt)
    if officer is None or not officer.is_active:
        burn_verify_time(pin)
        raise InvalidCredentialsError()
    return officer


def _open_session(
    db: Session, officer: Officer, device_label: str | None, now: datetime
) -> tuple[OfficerSession, str]:
    """New phone session. Returns (session, plain refresh token)."""
    refresh_token = new_refresh_token()
    session = OfficerSession(
        officer_id=officer.id,
        refresh_token_hash=hash_refresh_token(refresh_token),
        device_label=(device_label.strip() or None) if device_label else None,
        last_used_at=now,
        expires_at=now + timedelta(days=Settings.REFRESH_TOKEN_DAYS),
    )
    db.add(session)
    db.flush()  # assigns session.id
    return session, refresh_token


def authenticate(
    db: Session,
    *,
    facility_code: str | None,
    officer_code: str,
    pin: str,
    device_label: str | None = None,
    now: datetime | None = None,
) -> LoginResult:
    now = now or utcnow()
    officer = _find_login_officer(db, facility_code, officer_code, pin)
    _check_pin(db, officer, pin, now)
    _clear_pin_failures(officer)
    if needs_rehash(officer.pin_hash):
        officer.pin_hash = hash_pin(pin)

    session, refresh_token = _open_session(db, officer, device_label, now)
    access_token, access_expires_at = create_access_token(officer.id, session.id, now)
    facility = db.get(Facility, officer.facility_id) if officer.facility_id else None
    db.commit()
    return LoginResult(
        officer=officer,
        facility=facility,
        access_token=access_token,
        access_expires_at=access_expires_at,
        refresh_token=refresh_token,
        refresh_expires_at=session.expires_at,
        session_id=session.id,
    )


# ---- refresh / logout -----------------------------------------------------


def refresh_access(
    db: Session, refresh_token: str, now: datetime | None = None
) -> RefreshResult:
    now = now or utcnow()
    row = load_session_row(
        db,
        OfficerSession.refresh_token_hash == hash_refresh_token(refresh_token),
        lock=True,
    )
    if row is None:
        raise InvalidTokenError("Unknown refresh token.")
    assert_session_usable(row, now)

    session, officer, _ = row
    session.last_used_at = now
    session.expires_at = now + timedelta(days=Settings.REFRESH_TOKEN_DAYS)  # sliding
    access_token, access_expires_at = create_access_token(officer.id, session.id, now)
    result = RefreshResult(
        access_token=access_token,
        access_expires_at=access_expires_at,
        refresh_expires_at=session.expires_at,
    )
    db.commit()
    return result


def revoke_refresh_token(
    db: Session, refresh_token: str, now: datetime | None = None
) -> None:
    """Idempotent: an unknown or already-revoked token is a silent no-op, so
    logout always 'works' from the phone's point of view."""
    now = now or utcnow()
    session = db.scalar(
        select(OfficerSession)
        .where(OfficerSession.refresh_token_hash == hash_refresh_token(refresh_token))
        .with_for_update()
    )
    if session is not None and session.revoked_at is None:
        session.revoked_at = now
        db.commit()


# ---- change PIN -----------------------------------------------------------


def _check_new_pin(new_pin: str, officer: Officer) -> None:
    try:
        validate_pin_policy(new_pin)
    except ValueError as exc:
        raise WeakPinError(str(exc)) from exc
    if verify_pin(new_pin, officer.pin_hash):
        raise WeakPinError("New PIN must be different from the current one.")


def change_pin(
    db: Session,
    *,
    officer_id: uuid.UUID,
    session_id: uuid.UUID,
    current_pin: str,
    new_pin: str,
    now: datetime | None = None,
) -> None:
    """Set a new PIN, clear must_change_pin, and sign out every OTHER phone.
    The current PIN is re-checked (with lockout) so a stolen access token alone
    cannot take over the account."""
    now = now or utcnow()
    officer = db.scalar(select(Officer).where(Officer.id == officer_id).with_for_update())
    if officer is None or not officer.is_active:
        raise SessionRevokedError()

    _check_pin(db, officer, current_pin, now, message="Current PIN is incorrect.")
    _check_new_pin(new_pin, officer)

    officer.pin_hash = hash_pin(new_pin)
    officer.must_change_pin = False
    _clear_pin_failures(officer)
    revoke_sessions(db, officer.id, keep=session_id)
    db.commit()
