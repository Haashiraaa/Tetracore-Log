# backend/src/api/duty_service.py

"""Officers' duty log. Each officer logs themselves, from their own login: go on duty at a
gate (the signature is optional), change gate mid-shift, go off duty. Everything else an
officer logs (trucks, visitors, staff) needs them to be on duty first: see
entry_service.require_gate.

A change of gate closes the open stretch and opens a new one at the new gate; both carry the
same shift_id. facility_id and officer ids always come from the token."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.src.api import event_service
from backend.src.api.entry_service import facility_of
from backend.src.api.schemas import (
    CurrentOfficer,
    DutyChangeGateRequest,
    DutyEntryOut,
    DutyOffRequest,
    DutyOnRequest,
    DutyStatusOut,
)
from backend.src.api.signature import decode_signature_png
from backend.src.db.orm.tables import Event, Facility, Officer
from backend.src.db.queries import duty as q
from backend.src.exceptions.errors import (
    AlreadyOnDutyError,
    ConflictError,
    InvalidGateError,
    NotOnDutyError,
)
from backend.src.security.tokens import utcnow


def _facility(db: Session, facility_id: uuid.UUID) -> Facility:
    facility = db.get(Facility, facility_id)
    assert facility is not None
    return facility


def _name(db: Session, officer: CurrentOfficer) -> str:
    row = db.get(Officer, officer.officer_id)
    return row.full_name if row is not None else "An officer"


def _check_gate(facility: Facility, gate: int) -> None:
    if not 1 <= gate <= facility.gate_count:
        raise InvalidGateError(
            f"{facility.code} has {facility.gate_count} gate"
            f"{'' if facility.gate_count == 1 else 's'}. Pick one of them.")


def _out(db: Session, entry_id: uuid.UUID, facility_id: uuid.UUID) -> DutyEntryOut:
    row = q.get(db, entry_id, facility_id)
    assert row is not None
    return DutyEntryOut.from_row(row)


def _stored(db: Session, entry_id: uuid.UUID, facility_id: uuid.UUID) -> Any | None:
    """The row a retry already created. An id used by ANOTHER facility is a clash."""
    row = q.get(db, entry_id, None)
    if row is not None and row[0].facility_id != facility_id:
        raise ConflictError("That entry id is already in use.")
    return row


def status(db: Session, *, officer: CurrentOfficer) -> DutyStatusOut:
    facility_id = facility_of(officer)
    facility = _facility(db, facility_id)
    open_row = q.open_for_officer(db, officer.officer_id)
    return DutyStatusOut(
        facility_code=facility.code, gate_count=facility.gate_count,
        current=None if open_row is None else _out(db, open_row.id, facility_id))


def go_on(
    db: Session, *, officer: CurrentOfficer, data: DutyOnRequest
) -> tuple[DutyEntryOut, bool]:
    """Returns (entry, created). A retry with the same id returns the stored row."""
    facility_id = facility_of(officer)
    signature = decode_signature_png(data.signature)  # validate before any DB work
    stored = _stored(db, data.id, facility_id)
    if stored is not None:
        return DutyEntryOut.from_row(stored), False
    facility = _facility(db, facility_id)
    _check_gate(facility, data.gate)
    if q.open_for_officer(db, officer.officer_id) is not None:
        raise AlreadyOnDutyError()
    try:
        created = q.insert(
            db, id=data.id, facility_id=facility_id, officer_id=officer.officer_id,
            gate=data.gate, shift_id=data.id, on_duty_at=data.at or utcnow(),
            started_how="on", signature_in=signature, device_id=data.device_id)
        event = None
        if created:
            event = event_service.record(
                db, kind="officer_on_duty", facility_id=facility_id,
                actor_id=officer.officer_id, entry_id=data.id,
                summary=f"{_name(db, officer)} went on duty at gate {data.gate}.")
        db.commit()
    except IntegrityError:  # a parallel request put them on duty first
        db.rollback()
        raise AlreadyOnDutyError() from None
    if event is not None:
        event_service.announce(event.id)
    return _out(db, data.id, facility_id), created


def change_gate(
    db: Session, *, officer: CurrentOfficer, data: DutyChangeGateRequest
) -> tuple[DutyEntryOut, bool]:
    facility_id = facility_of(officer)
    stored = _stored(db, data.id, facility_id)
    if stored is not None:
        return DutyEntryOut.from_row(stored), False
    current = q.open_for_officer(db, officer.officer_id)
    if current is None:
        raise NotOnDutyError()
    facility = _facility(db, facility_id)
    _check_gate(facility, data.gate)
    if current.gate == data.gate:
        raise InvalidGateError(f"You are already at gate {data.gate}.")
    now = data.at or utcnow()
    old_gate = current.gate
    shift_id = current.shift_id
    try:
        q.close(db, current.id, at=now, ended_how="moved")
        q.insert(
            db, id=data.id, facility_id=facility_id, officer_id=officer.officer_id,
            gate=data.gate, shift_id=shift_id, on_duty_at=now, started_how="moved")
        event = event_service.record(
            db, kind="officer_gate_changed", facility_id=facility_id,
            actor_id=officer.officer_id, entry_id=data.id,
            summary=f"{_name(db, officer)} moved from gate {old_gate} to gate {data.gate}.")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Could not change gate. Try again.") from None
    event_service.announce(event.id)
    return _out(db, data.id, facility_id), True


def go_off(db: Session, *, officer: CurrentOfficer, data: DutyOffRequest) -> DutyStatusOut:
    """Idempotent: going off duty when not on duty changes nothing."""
    facility_id = facility_of(officer)
    signature = decode_signature_png(data.signature)
    current = q.open_for_officer(db, officer.officer_id)
    if current is not None:
        gate = current.gate
        closed = q.close(db, current.id, at=data.at or utcnow(), ended_how="off",
                         signature=signature)
        event = None
        if closed:
            event = event_service.record(
                db, kind="officer_off_duty", facility_id=facility_id,
                actor_id=officer.officer_id, entry_id=current.id,
                summary=f"{_name(db, officer)} went off duty (gate {gate}).")
        db.commit()
        if event is not None:
            event_service.announce(event.id)
    return status(db, officer=officer)


def end_duty_by_admin(
    db: Session, *, officer_id: uuid.UUID, actor_id: uuid.UUID, name: str,
    facility_id: uuid.UUID | None,
) -> Event | None:
    """An admin ends someone's duty (a forgotten sign-off, or the account was disabled).
    The event if they were on duty, else None. The caller commits, then announces."""
    current = q.open_for_officer(db, officer_id)
    if current is None:
        return None
    gate = current.gate
    if not q.close(db, current.id, at=utcnow(), ended_how="admin"):
        return None
    return event_service.record(
        db, kind="officer_off_duty", facility_id=facility_id, actor_id=actor_id,
        entry_id=current.id,
        summary=f"{name} was taken off duty by an admin (gate {gate}).")


def on_duty_now(db: Session, *, scope: uuid.UUID | None) -> list[DutyEntryOut]:
    return [DutyEntryOut.from_row(r) for r in q.on_duty_now(db, scope)]


