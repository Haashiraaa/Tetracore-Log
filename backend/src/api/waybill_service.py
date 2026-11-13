# backend/src/api/waybill_service.py

"""Waybill log rules. All of it is the shared entry rules (entry_service.py); this file
only says which model and which fields belong to couriers."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from backend.src.api import entry_service
from backend.src.api.schemas import (
    CurrentOfficer,
    PersonSignOutRequest,
    WaybillEntryOut,
    WaybillLookupOut,
    WaybillSignInRequest,
)
from backend.src.db.orm.tables import WaybillEntry


def _lookup_out(last: WaybillEntry, *, phone: str, open_entry_id: uuid.UUID | None,
                has_signature: bool) -> WaybillLookupOut:
    return WaybillLookupOut(
        full_name=last.full_name, phone=phone, open_entry_id=open_entry_id,
        has_signature=has_signature, came_by_vehicle=last.came_by_vehicle,
        plate_number=last.plate_number)


def sign_in(
    db: Session, *, officer: CurrentOfficer, data: WaybillSignInRequest
) -> tuple[WaybillEntryOut, bool]:
    """Returns (entry, created). A retry with the same id returns the stored entry."""
    row, created = entry_service.create_entry(
        db, officer=officer, model=WaybillEntry, data=data, reuse_signature=True,
        fields=data.model_dump(include={"full_name", "phone", "came_by_vehicle", "plate_number"})
        | {"items": [i.model_dump() for i in data.items]})
    return WaybillEntryOut.from_row(row), created


def lookup(db: Session, *, officer: CurrentOfficer, phone: str) -> WaybillLookupOut | None:
    """null = never signed in here. Otherwise what was written last time, to CONFIRM."""
    found = entry_service.lookup_by_phone(db, officer=officer, model=WaybillEntry, phone=phone)
    if found is None:
        return None
    last, open_entry_id = found
    signed = entry_service.phones_with_signature(
        db, officer=officer, model=WaybillEntry, phones=[phone])
    return _lookup_out(last, phone=phone, open_entry_id=open_entry_id,
                       has_signature=phone in signed)


def search(db: Session, *, officer: CurrentOfficer, digits: str) -> list[WaybillLookupOut]:
    """Up to 8 couriers whose phone contains what was typed, for the gate's suggestions."""
    found = entry_service.search_by_phone(db, officer=officer, model=WaybillEntry, digits=digits)
    signed = entry_service.phones_with_signature(
        db, officer=officer, model=WaybillEntry, phones=[last.phone for last, _ in found])
    return [_lookup_out(last, phone=last.phone, open_entry_id=open_id,
                        has_signature=last.phone in signed)
            for last, open_id in found]


def sign_out(
    db: Session, *, officer: CurrentOfficer, entry_id: uuid.UUID,
    data: PersonSignOutRequest,
) -> WaybillEntryOut:
    row = entry_service.close_entry(
        db, officer=officer, model=WaybillEntry, entry_id=entry_id,
        signed_out_at=data.signed_out_at, signature=data.signature,
        not_found="Waybill entry not found.", reuse_signature=True)
    return WaybillEntryOut.from_row(row)
