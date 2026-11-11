# backend/src/api/routes/visitors.py

"""Visitor log: sign in, sign out, list, signatures."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from backend.src.api import visitor_service
from backend.src.api.deps import get_facility_scope, require_entry_writer
from backend.src.api.routes._entries import EntryFilters, SignatureSide, signature_response
from backend.src.api.schemas import (
    CurrentOfficer,
    EntrySignOutRequest,
    VisitorEntryOut,
    VisitorSignInRequest,
)
from backend.src.db.queries import visitors as q
from backend.src.db.session import get_db

router = APIRouter(prefix="/visitors", tags=["visitors"])


@router.post("/entries", response_model=VisitorEntryOut, status_code=status.HTTP_201_CREATED)
def sign_in(
    body: VisitorSignInRequest,
    response: Response,
    officer: CurrentOfficer = Depends(require_entry_writer),
    db: Session = Depends(get_db),
) -> VisitorEntryOut:
    entry, created = visitor_service.sign_in(db, officer=officer, data=body)
    if not created:
        response.status_code = status.HTTP_200_OK  # idempotent replay
    return entry


@router.post("/entries/{entry_id}/sign-out", response_model=VisitorEntryOut)
def sign_out(
    entry_id: uuid.UUID,
    body: Optional[EntrySignOutRequest] = None,
    officer: CurrentOfficer = Depends(require_entry_writer),
    db: Session = Depends(get_db),
) -> VisitorEntryOut:
    return visitor_service.sign_out(db, officer=officer, entry_id=entry_id, data=body)


@router.get("/entries", response_model=list[VisitorEntryOut])
def list_entries(
    filters: EntryFilters = Depends(),
    scope: Optional[uuid.UUID] = Depends(get_facility_scope),
    db: Session = Depends(get_db),
) -> list[VisitorEntryOut]:
    rows = q.list_entries(db, scope=scope, **filters.as_kwargs())
    return [VisitorEntryOut.from_row(r) for r in rows]


@router.get("/entries/{entry_id}/signature")
def get_signature(
    entry_id: uuid.UUID,
    side: SignatureSide = "in",
    scope: Optional[uuid.UUID] = Depends(get_facility_scope),
    db: Session = Depends(get_db),
) -> Response:
    """The PNG signed on the way in (`?side=in`, default) or out (`?side=out`)."""
    return signature_response(q.get_signature(db, entry_id, scope, side))
