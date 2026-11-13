# backend/src/api/occurrence_service.py

"""Events log rules: an officer writes a note into the log. The server sets the time, the
officer and the gate; the signature is the officer's own, from their latest duty sign-on
(marked as reused), unless the request carries a fresh one. Notes are never edited or deleted.
Needs the officer to be on duty, like every other log."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.src.api import event_service
from backend.src.api.entry_service import facility_of, require_gate
from backend.src.api.schemas import (
    CurrentOfficer,
    OccurrenceCreateRequest,
    OccurrenceOut,
    SignatureOnFileOut,
)
from backend.src.api.signature import decode_signature_png
from backend.src.db.orm.tables import Officer
from backend.src.db.queries import occurrences as q
from backend.src.exceptions.errors import ConflictError, InvalidSignatureError
from backend.src.security.tokens import utcnow

_SUMMARY_NOTE_CHARS = 140


def _name(db: Session, officer: CurrentOfficer) -> str:
    row = db.get(Officer, officer.officer_id)
    return row.full_name if row is not None else "An officer"


def signature_on_file(db: Session, *, officer: CurrentOfficer) -> SignatureOnFileOut:
    return SignatureOnFileOut(has_signature=q.has_duty_signature(db, officer.officer_id))


def create(
    db: Session, *, officer: CurrentOfficer, data: OccurrenceCreateRequest
) -> tuple[OccurrenceOut, bool]:
    """Returns (note, created). A retry with the same id returns the stored note."""
    facility_id = facility_of(officer)
    drawn = decode_signature_png(data.signature)  # validate before any DB work
    stored = q.get(db, data.id, None)
    if stored is not None:
        if stored[0].facility_id != facility_id:
            raise ConflictError("That entry id is already in use.")
        return OccurrenceOut.from_row(stored), False
    reused = drawn is None
    signature = drawn if drawn is not None else q.duty_signature(db, officer.officer_id)
    if signature is None:
        raise InvalidSignatureError(
            "No signature on file for you. Sign when you go on duty, or sign this note.")
    gate = require_gate(db, officer)
    created = q.insert(
        db, id=data.id, facility_id=facility_id, officer_id=officer.officer_id, gate=gate,
        note=data.note, logged_at=data.logged_at or utcnow(), signature=signature,
        signature_reused=reused, device_id=data.device_id)
    event = None
    if created:  # a retry of the same note is not news
        text = data.note if len(data.note) <= _SUMMARY_NOTE_CHARS else (
            data.note[:_SUMMARY_NOTE_CHARS - 1].rstrip() + "…")
        event = event_service.record(
            db, kind="event_logged", facility_id=facility_id, actor_id=officer.officer_id,
            entry_id=data.id, summary=f"{_name(db, officer)} logged an event: {text}")
    db.commit()
    if event is not None:
        event_service.announce(event.id)
    row = q.get(db, data.id, facility_id)
    assert row is not None
    return OccurrenceOut.from_row(row), created
