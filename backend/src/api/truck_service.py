# backend/src/api/truck_service.py

"""Truck rules. facility_id and officer ids always come from the token.

V1 is online-first, so signing in a truck that is already inside is rejected
(409). Revisit that rule when offline sync lands."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from backend.src.api.entry_service import facility_of
from backend.src.api.schemas import (
    CurrentOfficer,
    TruckEntryOut,
    TruckLookupOut,
    TruckSignInRequest,
    TruckSignOutRequest,
)
from backend.src.api.signature import decode_signature_png
from backend.src.db.orm._helpers import normalize_plate
from backend.src.db.queries import trucks as q
from backend.src.exceptions.errors import (
    ConflictError,
    NotFoundError,
    TruckAlreadyInsideError,
)
from backend.src.security.tokens import utcnow


def lookup_by_plate(
    db: Session, *, officer: CurrentOfficer, plate: str
) -> TruckLookupOut | None:
    facility_id = facility_of(officer)
    truck = q.find_truck(db, facility_id, plate)
    if truck is None:
        return None
    return TruckLookupOut(
        truck_id=truck.id,
        plate_number=truck.plate_number,
        driver_name=truck.driver_name,
        driver_phone=truck.driver_phone,
        company=truck.company,
        open_entry_id=q.find_open_entry_id(db, facility_id, truck.id),
    )


def _stored_entry(db: Session, entry_id: uuid.UUID, facility_id: uuid.UUID) -> Any | None:
    """The row a retry already created, or None. Another facility's id is a clash."""
    existing = q.get_entry(db, entry_id, None)
    if existing is not None and existing[0].facility_id != facility_id:
        raise ConflictError("That entry id is already in use.")
    return existing


def _register_truck(db: Session, facility_id: uuid.UUID, data: TruckSignInRequest) -> uuid.UUID:
    """Upsert the truck and make sure it is not already inside."""
    truck_id = q.upsert_truck(
        db, facility_id=facility_id, plate=data.plate_number,
        driver_name=data.driver_name, driver_phone=data.driver_phone,
        company=data.company)
    if q.find_open_entry_id(db, facility_id, truck_id) is not None:
        db.rollback()
        raise TruckAlreadyInsideError(
            f"Truck {normalize_plate(data.plate_number)} is already inside. "
            "Sign it out first.")
    return truck_id


def _insert_visit(
    db: Session, officer: CurrentOfficer, facility_id: uuid.UUID,
    truck_id: uuid.UUID, data: TruckSignInRequest, signature: bytes | None,
) -> bool:
    return q.insert_entry(
        db, entry_id=data.id, facility_id=facility_id, truck_id=truck_id,
        plate=data.plate_number, driver_name=data.driver_name,
        driver_phone=data.driver_phone, company=data.company,
        scm_purchased=data.scm_purchased,
        signed_in_at=data.signed_in_at or utcnow(), signature_in=signature,
        signed_in_by=officer.officer_id, device_id=data.device_id)


def sign_in(
    db: Session, *, officer: CurrentOfficer, data: TruckSignInRequest
) -> tuple[TruckEntryOut, bool]:
    """Returns (entry, created). A retry with the same id returns the stored
    entry untouched (created=False)."""
    facility_id = facility_of(officer)
    signature = decode_signature_png(data.signature)  # validate before any DB work

    stored = _stored_entry(db, data.id, facility_id)
    if stored is not None:
        return TruckEntryOut.from_row(stored), False

    truck_id = _register_truck(db, facility_id, data)
    created = _insert_visit(db, officer, facility_id, truck_id, data, signature)
    db.commit()

    row = q.get_entry(db, data.id, facility_id)
    assert row is not None
    return TruckEntryOut.from_row(row), created


def sign_out(
    db: Session, *, officer: CurrentOfficer, entry_id: uuid.UUID,
    data: TruckSignOutRequest | None,
) -> TruckEntryOut:
    """Idempotent: a repeat returns the stored entry, first sign-out wins."""
    facility_id = facility_of(officer)
    data = data or TruckSignOutRequest()
    q.sign_out_entry(
        db, entry_id=entry_id, facility_id=facility_id,
        officer_id=officer.officer_id,
        signed_out_at=data.signed_out_at or utcnow(),
        scm_purchased=data.scm_purchased)
    db.commit()
    row = q.get_entry(db, entry_id, facility_id)
    if row is None:
        raise NotFoundError("Truck entry not found.")
    return TruckEntryOut.from_row(row)
