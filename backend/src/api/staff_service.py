# backend/src/api/staff_service.py

"""Staff log rules. All of it is the shared entry rules (entry_service.py); this file
only says which model and which fields belong to staffs."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from backend.src.api import entry_service
from backend.src.api.schemas import (
    CurrentOfficer,
    EntrySignOutRequest,
    StaffEntryOut,
    StaffSignInRequest,
)
from backend.src.db.orm.tables import StaffEntry


def sign_in(
    db: Session, *, officer: CurrentOfficer, data: StaffSignInRequest
) -> tuple[StaffEntryOut, bool]:
    """Returns (entry, created). A retry with the same id returns the stored entry."""
    row, created = entry_service.create_entry(
        db, officer=officer, model=StaffEntry, data=data,
        fields=data.model_dump(include={"full_name"}))
    return StaffEntryOut.from_row(row), created


def sign_out(
    db: Session, *, officer: CurrentOfficer, entry_id: uuid.UUID,
    data: EntrySignOutRequest | None,
) -> StaffEntryOut:
    data = data or EntrySignOutRequest()
    row = entry_service.close_entry(
        db, officer=officer, model=StaffEntry, entry_id=entry_id,
        signed_out_at=data.signed_out_at, signature=data.signature,
        not_found="Staff entry not found.")
    return StaffEntryOut.from_row(row)
