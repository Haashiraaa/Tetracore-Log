

# backend/src/security/sessions.py

"""Sign phones out. Shared by the API (admin routes, change PIN) and the admin CLI."""

from __future__ import annotations

import uuid

from sqlalchemy import update
from sqlalchemy.orm import Session

from backend.src.db.orm.tables import OfficerSession
from backend.src.security.tokens import utcnow


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
