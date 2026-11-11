# backend/src/api/entry_service.py

"""Rules every log (trucks, visitors, staff) shares: who may write, retries, first
sign-out wins. A log's own service builds on these. facility_id and officer ids always
come from the token, never from the request."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.src.api.schemas import CurrentOfficer
from backend.src.api.signature import decode_signature_png
from backend.src.db.queries import _entries
from backend.src.exceptions.errors import ConflictError, NotFoundError, PermissionDeniedError
from backend.src.security.tokens import utcnow


def facility_of(officer: CurrentOfficer) -> uuid.UUID:
    """The facility an entry is written to."""
    if not officer.can_write_entries or officer.facility_id is None:
        raise PermissionDeniedError(
            "Only accounts that belong to a facility can write log entries.")
    return officer.facility_id


def stored_entry(
    db: Session, model: Any, entry_id: uuid.UUID, facility_id: uuid.UUID
) -> Any | None:
    """The row a retry already created, or None. An id used by ANOTHER facility is a clash."""
    existing = _entries.get_entry(db, model, entry_id, None)
    if existing is not None and existing[0].facility_id != facility_id:
        raise ConflictError("That entry id is already in use.")
    return existing


def create_entry(
    db: Session,
    *,
    officer: CurrentOfficer,
    model: Any,
    data: Any,
    fields: dict[str, Any],
) -> tuple[Any, bool]:
    """Sign someone in. `data` is the request (an EntrySignInRequest), `fields` the log's own
    columns. Returns (row, created); a retry with the same id returns the stored row."""
    facility_id = facility_of(officer)
    signature = decode_signature_png(data.signature)  # validate before any DB work
    stored = stored_entry(db, model, data.id, facility_id)
    if stored is not None:
        return stored, False
    created = _entries.insert_entry(
        db, model, id=data.id, facility_id=facility_id,
        signed_in_at=data.signed_in_at or utcnow(), signature_in=signature,
        signed_in_by=officer.officer_id, device_id=data.device_id, **fields)
    db.commit()
    row = _entries.get_entry(db, model, data.id, facility_id)
    assert row is not None
    return row, created


def close_entry(
    db: Session,
    *,
    officer: CurrentOfficer,
    model: Any,
    entry_id: uuid.UUID,
    signed_out_at: Optional[datetime] = None,
    signature: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
    not_found: str = "Entry not found.",
) -> Any:
    """Sign someone out. Idempotent: a repeat returns the stored row, first sign-out wins."""
    facility_id = facility_of(officer)
    png = decode_signature_png(signature)
    _entries.sign_out_entry(
        db, model, entry_id=entry_id, facility_id=facility_id,
        officer_id=officer.officer_id, signed_out_at=signed_out_at or utcnow(),
        signature=png, extra=extra)
    db.commit()
    row = _entries.get_entry(db, model, entry_id, facility_id)
    if row is None:
        raise NotFoundError(not_found)
    return row
