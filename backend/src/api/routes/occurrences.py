# backend/src/api/routes/occurrences.py

"""Events log (officer notes): write a note, list, signature. The app calls it "Events";
it is `occurrences` here so it is not confused with `/events`, the alerts feed."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from backend.src.api import occurrence_service
from backend.src.api.deps import get_facility_scope, require_entry_writer
from backend.src.api.routes._entries import EntryFilters, signature_response
from backend.src.api.schemas import (
    CurrentOfficer,
    OccurrenceCreateRequest,
    OccurrenceOut,
    SignatureOnFileOut,
)
from backend.src.db.queries import occurrences as q
from backend.src.db.session import get_db

router = APIRouter(prefix="/occurrences", tags=["events log"])


@router.get("/signature-on-file", response_model=SignatureOnFileOut)
def signature_on_file(
    officer: CurrentOfficer = Depends(require_entry_writer),
    db: Session = Depends(get_db),
) -> SignatureOnFileOut:
    """Can this officer's duty signature be used for a note, or must they sign it?"""
    return occurrence_service.signature_on_file(db, officer=officer)


@router.post("", response_model=OccurrenceOut, status_code=status.HTTP_201_CREATED)
def create(
    body: OccurrenceCreateRequest,
    response: Response,
    officer: CurrentOfficer = Depends(require_entry_writer),
    db: Session = Depends(get_db),
) -> OccurrenceOut:
    note, created = occurrence_service.create(db, officer=officer, data=body)
    if not created:
        response.status_code = status.HTTP_200_OK  # idempotent replay
    return note


@router.get("", response_model=list[OccurrenceOut])
def list_entries(
    filters: EntryFilters = Depends(),
    scope: Optional[uuid.UUID] = Depends(get_facility_scope),
    db: Session = Depends(get_db),
) -> list[OccurrenceOut]:
    rows = q.list_entries(db, scope=scope, **filters.as_kwargs())
    return [OccurrenceOut.from_row(r) for r in rows]


@router.get("/{note_id}/signature")
def get_signature(
    note_id: uuid.UUID,
    scope: Optional[uuid.UUID] = Depends(get_facility_scope),
    db: Session = Depends(get_db),
) -> Response:
    """The officer's PNG signature on this note."""
    return signature_response(q.get_signature(db, note_id, scope))
