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


def sign_out(
    db: Session, *, officer: CurrentOfficer, entry_id: uuid.UUID,
    data: EntrySignOutRequest | None,
) -> VisitorEntryOut:
    data = data or EntrySignOutRequest()
    row = entry_service.close_entry(
        db, officer=officer, model=VisitorEntry, entry_id=entry_id,
        signed_out_at=data.signed_out_at, signature=data.signature,
        not_found="Visitor entry not found.")
    return VisitorEntryOut.from_row(row)
