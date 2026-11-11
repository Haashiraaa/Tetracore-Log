# backend/src/api/routes/staff.py

"""Staff log. SPACE ONLY: reading works now. Signing in and out is added once the
details to record are decided (schemas/staff.py, db/queries/staff.py)."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from backend.src.api.deps import get_facility_scope
from backend.src.api.routes._entries import EntryFilters, signature_response
from backend.src.api.schemas import StaffEntryOut
from backend.src.db.queries import staff as q
from backend.src.db.session import get_db

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/entries", response_model=list[StaffEntryOut])
def list_entries(
    filters: EntryFilters = Depends(),
    scope: Optional[uuid.UUID] = Depends(get_facility_scope),
    db: Session = Depends(get_db),
) -> list[StaffEntryOut]:
    rows = q.list_entries(db, scope=scope, **filters.as_kwargs())
    return [StaffEntryOut.from_row(r) for r in rows]


@router.get("/entries/{entry_id}/signature")
def get_signature(
    entry_id: uuid.UUID,
    scope: Optional[uuid.UUID] = Depends(get_facility_scope),
    db: Session = Depends(get_db),
) -> Response:
    return signature_response(q.get_signature(db, entry_id, scope))
