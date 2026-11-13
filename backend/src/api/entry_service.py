# backend/src/api/entry_service.py

"""Rules every log (trucks, visitors, staff) shares: who may write, retries, first
sign-out wins. A log's own service builds on these. facility_id and officer ids always
come from the token, never from the request."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional, Sequence

from sqlalchemy import ColumnElement
from sqlalchemy.orm import Session

from backend.src.api import event_service
from backend.src.api.schemas import CurrentOfficer
from backend.src.api.signature import decode_signature_png
from backend.src.db.orm.tables import StaffEntry, TruckEntry, VisitorEntry
from backend.src.db.queries import _entries
from backend.src.db.queries import duty as duty_q
from backend.src.exceptions.errors import (
    AlreadyInsideError,
    ConflictError,
    InvalidSignatureError,
    NotFoundError,
    NotOnDutyError,
    PermissionDeniedError,
)
from backend.src.security.tokens import utcnow

_LOG_NAME = {TruckEntry: "truck", VisitorEntry: "visitor", StaffEntry: "staff"}


def _who(entry: Any) -> str:
    """How an entry reads in a notification: "Truck LAG123AB" or the person's full name."""
    plate = getattr(entry, "plate_number", None)
    return f"Truck {plate}" if plate else entry.full_name


def facility_of(officer: CurrentOfficer) -> uuid.UUID:
    """The facility an entry is written to."""
    if not officer.can_write_entries or officer.facility_id is None:
        raise PermissionDeniedError(
            "Only accounts that belong to a facility can write log entries.")
    return officer.facility_id


def require_gate(db: Session, officer: CurrentOfficer) -> int:
    """The gate this officer is on duty at. Nobody logs anything without being on duty."""
    gate = duty_q.open_gate(db, officer.officer_id)
    if gate is None:
        raise NotOnDutyError()
    return gate


def stored_entry(
    db: Session, model: Any, entry_id: uuid.UUID, facility_id: uuid.UUID
) -> Any | None:
    """The row a retry already created, or None. An id used by ANOTHER facility is a clash."""
    existing = _entries.get_entry(db, model, entry_id, None)
    if existing is not None and existing[0].facility_id != facility_id:
        raise ConflictError("That entry id is already in use.")
    return existing


def lookup_by_phone(
    db: Session, *, officer: CurrentOfficer, model: Any, phone: str
) -> tuple[Any, uuid.UUID | None] | None:
    """For logs that identify a person by phone (visitors, staff). None = never seen here.
    Otherwise (their latest entry, the id of the entry they are inside on, if any).
    `phone` is already canonical."""
    facility_id = facility_of(officer)
    last = _entries.latest_by_phone(db, model, facility_id, phone)
    if last is None:
        return None
    return last, _entries.open_id_by_phone(db, model, facility_id, phone)


def search_by_phone(
    db: Session, *, officer: CurrentOfficer, model: Any, digits: str, limit: int = 8
) -> list[tuple[Any, uuid.UUID | None]]:
    """Search-as-you-type over phones already seen in this facility.
    `digits` comes from models.phone_search_digits."""
    return _entries.search_by_phone(db, model, facility_of(officer), digits, limit)


def phones_with_signature(
    db: Session, *, officer: CurrentOfficer, model: Any, phones: Sequence[str]
) -> set[str]:
    """Which of these phones already have a signature on file in this officer's facility."""
    return _entries.phones_with_signature(db, model, facility_of(officer), phones)


def refuse_if_inside(
    db: Session, *, facility_id: uuid.UUID, model: Any, phone: str, entry_id: uuid.UUID
) -> None:
    """One sign-in at a time: someone inside must sign out before signing in again.
    A retry of the same entry (same id) is not refused: it replays."""
    open_id = _entries.open_id_by_phone(db, model, facility_id, phone)
    if open_id is not None and open_id != entry_id:
        raise AlreadyInsideError()


def create_entry(
    db: Session,
    *,
    officer: CurrentOfficer,
    model: Any,
    data: Any,
    fields: dict[str, Any],
    reuse_signature: bool = False,
) -> tuple[Any, bool]:
    """Sign someone in. `data` is the request (an EntrySignInRequest), `fields` the log's own
    columns. Returns (row, created); a retry with the same id returns the stored row.
    `reuse_signature` (people logs): no signature in the request means "use the one this
    phone gave last time"; if there is none on file the request is refused."""
    facility_id = facility_of(officer)
    signature = decode_signature_png(data.signature)  # validate before any DB work
    stored = stored_entry(db, model, data.id, facility_id)
    if stored is not None:
        return stored, False
    if signature is None and reuse_signature and fields.get("phone"):
        signature = _entries.latest_signature_by_phone(
            db, model, facility_id, fields["phone"])
    if signature is None:
        raise InvalidSignatureError(
            "No signature on file for this phone number. Ask them to sign.")
    gate = require_gate(db, officer)
    if fields.get("phone"):  # people are found by phone: only one open sign-in each
        try:
            refuse_if_inside(db, facility_id=facility_id, model=model,
                             phone=fields["phone"], entry_id=data.id)
        except AlreadyInsideError:
            warning = event_service.record(
                db, kind="already_inside", facility_id=facility_id,
                actor_id=officer.officer_id,
                summary=f"{fields['full_name']} tried to sign in but is already inside.")
            db.commit()
            event_service.announce(warning.id)
            raise
    created = _entries.insert_entry(
        db, model, id=data.id, facility_id=facility_id,
        signed_in_at=data.signed_in_at or utcnow(), signature_in=signature,
        signed_in_by=officer.officer_id, device_id=data.device_id, gate_in=gate, **fields)
    event = None
    if created:  # a retry of the same entry is not news
        event = event_service.record(
            db, kind=f"{_LOG_NAME[model]}_in", facility_id=facility_id,
            actor_id=officer.officer_id, entry_id=data.id,
            summary=f"{fields['full_name']} signed in.")
    db.commit()
    if event is not None:
        event_service.announce(event.id)
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
    require: Sequence[ColumnElement[bool]] = (),
    not_found: str = "Entry not found.",
    reuse_signature: bool = False,
) -> Any:
    """Sign someone out. Idempotent: a repeat returns the stored row, first sign-out wins
    (and needs no duty: it changes nothing). `reuse_signature` (people logs): no signature
    in the request means "use the one given at sign-in"."""
    facility_id = facility_of(officer)
    png = decode_signature_png(signature)
    row = _entries.get_entry(db, model, entry_id, facility_id)
    if row is None:
        raise NotFoundError(not_found)
    if row[0].signed_out_at is not None:
        return row
    gate = require_gate(db, officer)
    if png is None and reuse_signature:
        sig_row = _entries.get_signature(db, model, entry_id, facility_id, "in")
        png = sig_row[0] if sig_row is not None else None
        if png is None:
            raise InvalidSignatureError(
                "There is no sign-in signature to reuse. Ask them to sign.")
    closed = _entries.sign_out_entry(
        db, model, entry_id=entry_id, facility_id=facility_id,
        officer_id=officer.officer_id, signed_out_at=signed_out_at or utcnow(),
        signature=png, extra={"gate_out": gate, **(extra or {})}, require=require)
    row = _entries.get_entry(db, model, entry_id, facility_id)
    event = None
    if closed and row is not None:  # a repeat sign-out is not news
        event = event_service.record(
            db, kind=f"{_LOG_NAME[model]}_out", facility_id=facility_id,
            actor_id=officer.officer_id, entry_id=entry_id,
            summary=f"{_who(row[0])} signed out.")
    db.commit()
    if event is not None:
        event_service.announce(event.id)
    if row is None:
        raise NotFoundError(not_found)
    return row
