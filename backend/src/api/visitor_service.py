# backend/src/api/visitor_service.py

"""Visitor log rules. All of it is the shared entry rules (entry_service.py); this file
only says which model and which fields belong to visitors."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from backend.src.api import entry_service
from backend.src.api.schemas import (
    CurrentOfficer,
    EntrySignOutRequest,
    VisitorEntryOut,
    VisitorLookupOut,
    VisitorSignInRequest,
)
from backend.src.db.orm.tables import VisitorEntry


def sign_in(
    db: Session, *, officer: CurrentOfficer, data: VisitorSignInRequest
) -> tuple[VisitorEntryOut, bool]:
    """Returns (entry, created). A retry with the same id returns the stored entry."""
    row, created = entry_service.create_entry(
        db, officer=officer, model=VisitorEntry, data=data,
        fields=data.model_dump(
            include={"full_name", "company", "purpose", "items_received", "phone"}))
    return VisitorEntryOut.from_row(row), created


def lookup(db: Session, *, officer: CurrentOfficer, phone: str) -> VisitorLookupOut | None:
    """null = never signed in here. Otherwise what was written last time, to CONFIRM."""
    found = entry_service.lookup_by_phone(db, officer=officer, model=VisitorEntry, phone=phone)
    if found is None:
        return None
    last, open_entry_id = found
    return VisitorLookupOut(full_name=last.full_name, company=last.company,
                            phone=phone, open_entry_id=open_entry_id)


def search(db: Session, *, officer: CurrentOfficer, digits: str) -> list[VisitorLookupOut]:
    """Up to 8 people whose phone contains what was typed, for the gate's suggestions."""
    found = entry_service.search_by_phone(db, officer=officer, model=VisitorEntry, digits=digits)
    return [VisitorLookupOut(full_name=last.full_name, company=last.company, phone=last.phone,
                  open_entry_id=open_id) for last, open_id in found]


def sign_out(
    db: Session, *, officer: CurrentOfficer, entry_id: uuid.UUID,
    data: EntrySignOutRequest,
) -> VisitorEntryOut:
    row = entry_service.close_entry(
        db, officer=officer, model=VisitorEntry, entry_id=entry_id,
        signed_out_at=data.signed_out_at, signature=data.signature,
        not_found="Visitor entry not found.")
    return VisitorEntryOut.from_row(row)
