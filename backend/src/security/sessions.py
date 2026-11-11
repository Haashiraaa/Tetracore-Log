

# backend/src/security/sessions.py

"""Sign phones out. Shared by the API (admin routes, change PIN) and the admin CLI."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.src.db.orm.tables import Facility, Officer, OfficerSession
from backend.src.exceptions.errors import SessionRevokedError
from backend.src.security.tokens import utcnow

SessionRow = tuple[OfficerSession, Officer, bool | None]


def load_session_row(
    db: Session, *conditions: Any, lock: bool = False
) -> SessionRow | None:
    """(session, officer, facility_active) for the first row matching `conditions`.
    `facility_active` is None for a global account. `lock` row-locks the session."""
    stmt = (
        select(OfficerSession, Officer, Facility.is_active)
        .join(Officer, Officer.id == OfficerSession.officer_id)
        .outerjoin(Facility, Facility.id == Officer.facility_id)
        .where(*conditions)
    )
    if lock:
        stmt = stmt.with_for_update(of=OfficerSession)
    row = db.execute(stmt).first()
    return None if row is None else (row[0], row[1], row[2])


def assert_session_usable(row: SessionRow, now: datetime) -> None:
    """Single source of truth for 'may this session act right now?'.
    Used by /auth/refresh AND by the get_current_officer dependency."""
    session, officer, facility_active = row
    if session.revoked_at is not None or session.expires_at <= now:
        raise SessionRevokedError()
    if not officer.is_active:
        raise SessionRevokedError("This account has been disabled.")
    if officer.facility_id is not None and facility_active is not True:
        raise SessionRevokedError("This facility has been disabled.")


def revoke_sessions(
    db: Session, officer_id: uuid.UUID, *, keep: uuid.UUID | None = None
) -> None:
    """Revoke every live session of an officer, except `keep` (the phone in hand).
    Caller commits."""
    stmt = update(OfficerSession).where(
        OfficerSession.officer_id == officer_id,
        OfficerSession.revoked_at.is_(None),
    )
    if keep is not None:
        stmt = stmt.where(OfficerSession.id != keep)
    db.execute(stmt.values(revoked_at=utcnow()))
