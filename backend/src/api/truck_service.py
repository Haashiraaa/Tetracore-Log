# backend/src/api/truck_service.py

"""Truck rules. facility_id and officer ids always come from the token.

A truck's visit has a status: Queued (registered, still outside) -> On site (let in, the
driver signs) -> Departed (signed out). Or Queued -> Left queue (gave up, with a reason).
Every step needs the officer to be on duty; the gate they stand at is recorded.

V1 is online-first, so registering a truck that is already queued or inside is rejected
(409). Revisit that rule when offline sync lands."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from backend.src.api import event_service
from backend.src.api.entry_service import (
    close_entry,
    facility_of,
    require_gate,
    stored_entry,
)
from backend.src.api.schemas import (
    CurrentOfficer,
    TruckEnterRequest,
    TruckEntryOut,
    TruckLeaveQueueRequest,
    TruckLookupOut,
    TruckSignInRequest,
    TruckSignOutRequest,
)
from backend.src.api.signature import decode_signature_png
from backend.src.db.orm._helpers import normalize_plate
from backend.src.db.orm.tables import TruckEntry
from backend.src.db.queries import trucks as q
from backend.src.exceptions.errors import (
    InvalidSignatureError,
    InvalidTruckStateError,
    NotFoundError,
    TruckAlreadyInsideError,
)
from backend.src.security.tokens import utcnow

_NOT_FOUND = "Truck entry not found."


def lookup_by_plate(
    db: Session, *, officer: CurrentOfficer, plate: str
) -> TruckLookupOut | None:
    facility_id = facility_of(officer)
    truck = q.find_truck(db, facility_id, plate)
    if truck is None:
        return None
    open_entry = q.find_open_entry(db, facility_id, truck.id)
    return TruckLookupOut(
        has_signature=q.has_signature(db, facility_id, truck.id),
        truck_id=truck.id,
        plate_number=truck.plate_number,
        driver_name=truck.driver_name,
        driver_phone=truck.driver_phone,
        company=truck.company,
        cab_number=truck.cab_number,
        open_entry_id=None if open_entry is None else open_entry[0],
        open_entry_status=None if open_entry is None else open_entry[1],
    )


def _signature_to_use(
    db: Session, facility_id: uuid.UUID, plate: str, drawn: bytes | None
) -> tuple[bytes, bool]:
    """(signature, reused). The one drawn now, else the one on file for this plate at this
    facility. Refused when there is neither: a truck is never let in unsigned."""
    if drawn is not None:
        return drawn, False
    truck = q.find_truck(db, facility_id, plate)
    on_file = None if truck is None else q.latest_signature(db, facility_id, truck.id)
    if on_file is None:
        raise InvalidSignatureError("No signature on file for this truck. Ask the driver to sign.")
    return on_file, True


def _register_truck(db: Session, facility_id: uuid.UUID, data: TruckSignInRequest) -> uuid.UUID:
    """Upsert the truck and make sure it is not already queued or inside."""
    truck_id = q.upsert_truck(
        db, facility_id=facility_id, plate=data.plate_number,
        driver_name=data.driver_name, driver_phone=data.driver_phone,
        company=data.company, cab_number=data.cab_number)
    open_entry = q.find_open_entry(db, facility_id, truck_id)
    if open_entry is not None:
        db.rollback()
        plate = normalize_plate(data.plate_number)
        where = "in the queue" if open_entry[1] == "queued" else "inside"
        raise TruckAlreadyInsideError(
            f"Truck {plate} is already {where}. "
            + ("Let it in or mark it as left the queue first." if open_entry[1] == "queued"
               else "Sign it out first."))
    return truck_id


def sign_in(
    db: Session, *, officer: CurrentOfficer, data: TruckSignInRequest
) -> tuple[TruckEntryOut, bool]:
    """Register a truck: into the queue, or straight in with `enter_now`. Returns
    (entry, created). A retry with the same id returns the stored entry untouched."""
    facility_id = facility_of(officer)
    drawn = decode_signature_png(data.signature)  # validate before any DB work

    stored = stored_entry(db, TruckEntry, data.id, facility_id)
    if stored is not None:
        return TruckEntryOut.from_row(stored), False
    signature, reused = None, False
    if data.enter_now:  # letting it in needs a signature: drawn, or this plate's on file
        signature, reused = _signature_to_use(db, facility_id, data.plate_number, drawn)

    gate = require_gate(db, officer)
    plate = normalize_plate(data.plate_number)
    try:
        truck_id = _register_truck(db, facility_id, data)
    except TruckAlreadyInsideError:  # _register_truck rolled back: write the warning fresh
        warning = event_service.record(
            db, kind="already_inside", facility_id=facility_id, actor_id=officer.officer_id,
            summary=f"Truck {plate} tried to sign in but is already queued or inside.")
        db.commit()
        event_service.announce(warning.id)
        raise
    now = data.signed_in_at or utcnow()
    values: dict[str, Any] = dict(
        entry_id=data.id, facility_id=facility_id, truck_id=truck_id,
        plate=data.plate_number, driver_name=data.driver_name,
        driver_phone=data.driver_phone, company=data.company,
        cab_number=data.cab_number, scm_purchased=data.scm_purchased, signed_in_at=now,
        signed_in_by=officer.officer_id, device_id=data.device_id, queued_gate=gate)
    if data.enter_now:
        values.update(status="on_site", entered_at=now, entered_by=officer.officer_id,
                      gate_in=gate, signature_in=signature, signature_in_reused=reused)
    else:
        values.update(status="queued")
    created = q.insert_entry(db, **values)
    event = None
    if created:  # a retry of the same visit is not news
        if data.enter_now:
            event = event_service.record(
                db, kind="truck_in", facility_id=facility_id, actor_id=officer.officer_id,
                entry_id=data.id,
                summary=f"Truck {plate} signed in, driver {data.driver_name}.")
        else:
            event = event_service.record(
                db, kind="truck_queued", facility_id=facility_id,
                actor_id=officer.officer_id, entry_id=data.id,
                summary=f"Truck {plate} joined the queue, driver {data.driver_name}.")
    db.commit()
    if event is not None:
        event_service.announce(event.id)

    row = q.get_entry(db, data.id, facility_id)
    assert row is not None
    return TruckEntryOut.from_row(row), created


def _visit(db: Session, facility_id: uuid.UUID, entry_id: uuid.UUID) -> TruckEntry:
    row = q.get_entry(db, entry_id, facility_id)
    if row is None:
        raise NotFoundError(_NOT_FOUND)
    return row[0]


def enter(
    db: Session, *, officer: CurrentOfficer, entry_id: uuid.UUID, data: TruckEnterRequest
) -> TruckEntryOut:
    """Let a queued truck in. Idempotent: a truck already on site (or gone) comes back as
    stored; first one wins."""
    facility_id = facility_of(officer)
    drawn = decode_signature_png(data.signature)
    visit = _visit(db, facility_id, entry_id)
    if visit.status == "queued":
        signature, reused = _signature_to_use(db, facility_id, visit.plate_number, drawn)
        gate = require_gate(db, officer)
        moved = q.update_open_entry(
            db, entry_id=entry_id, facility_id=facility_id, from_status="queued",
            status="on_site", entered_at=data.entered_at or utcnow(),
            entered_by=officer.officer_id, gate_in=gate, signature_in=signature,
            signature_in_reused=reused)
        event = None
        if moved:
            event = event_service.record(
                db, kind="truck_in", facility_id=facility_id, actor_id=officer.officer_id,
                entry_id=entry_id,
                summary=f"Truck {visit.plate_number} signed in, driver {visit.driver_name}.")
        db.commit()
        if event is not None:
            event_service.announce(event.id)
    row = q.get_entry(db, entry_id, facility_id)
    assert row is not None
    return TruckEntryOut.from_row(row)


def leave_queue(
    db: Session, *, officer: CurrentOfficer, entry_id: uuid.UUID,
    data: TruckLeaveQueueRequest,
) -> TruckEntryOut:
    """A queued truck gave up. Only a queued truck can: one already inside signs out.
    Idempotent for a truck that has already left the queue."""
    facility_id = facility_of(officer)
    visit = _visit(db, facility_id, entry_id)
    if visit.status == "on_site" or visit.status == "departed":
        raise InvalidTruckStateError(
            f"Truck {visit.plate_number} is not in the queue "
            f"({'inside' if visit.status == 'on_site' else 'already left'}).")
    if visit.status == "queued":
        gate = require_gate(db, officer)
        moved = q.update_open_entry(
            db, entry_id=entry_id, facility_id=facility_id, from_status="queued",
            status="left_queue", left_queue_reason=data.reason,
            signed_out_at=data.left_at or utcnow(), signed_out_by=officer.officer_id,
            gate_out=gate)
        event = None
        if moved:
            event = event_service.record(
                db, kind="truck_left_queue", facility_id=facility_id,
                actor_id=officer.officer_id, entry_id=entry_id,
                summary=f"Truck {visit.plate_number} left the queue: {data.reason}")
        db.commit()
        if event is not None:
            event_service.announce(event.id)
    row = q.get_entry(db, entry_id, facility_id)
    assert row is not None
    return TruckEntryOut.from_row(row)


def sign_out(
    db: Session, *, officer: CurrentOfficer, entry_id: uuid.UUID,
    data: TruckSignOutRequest,
) -> TruckEntryOut:
    """Idempotent: a repeat returns the stored entry, first sign-out wins. Only a truck
    that is on site signs out: a queued one is let in or marked as left the queue."""
    facility_id = facility_of(officer)
    visit = _visit(db, facility_id, entry_id)
    if visit.status == "queued":
        raise InvalidTruckStateError(
            f"Truck {visit.plate_number} is still in the queue. Let it in first, "
            "or mark it as left the queue.")
    extra: dict[str, object] = {"status": "departed"}
    if data.scm_purchased is not None:
        extra["scm_purchased"] = data.scm_purchased
    row = close_entry(
        db, officer=officer, model=TruckEntry, entry_id=entry_id,
        signed_out_at=data.signed_out_at, signature=data.signature, extra=extra,
        require=[TruckEntry.status == "on_site"], not_found=_NOT_FOUND,
        reuse_signature=True)
    return TruckEntryOut.from_row(row)
