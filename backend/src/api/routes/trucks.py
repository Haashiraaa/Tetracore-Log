

# backend/src/api/routes/trucks.py

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from backend.src.api import truck_service
from backend.src.api.deps import get_facility_scope, require_entry_writer
from backend.src.api.routes._entries import EntryFilters, SignatureSide, signature_response
from backend.src.api.schemas import (
    CurrentOfficer,
    TruckEnterRequest,
    TruckEntryOut,
    TruckLeaveQueueRequest,
    TruckLookupOut,
    TruckSignInRequest,
    TruckSignOutRequest,
)
from backend.src.db.queries import trucks as q
from backend.src.db.session import get_db

router = APIRouter(prefix="/trucks", tags=["trucks"])


# ---- writes: accounts that belong to a facility ----

@router.get("/lookup", response_model=Optional[TruckLookupOut])
def lookup(
    plate: str = Query(min_length=2, max_length=40),
    officer: CurrentOfficer = Depends(require_entry_writer),
    db: Session = Depends(get_db),
) -> Optional[TruckLookupOut]:
    """null = new truck. Otherwise stored driver details to CONFIRM, plus
    open_entry_id and open_entry_status if the truck is queued or inside."""
    return truck_service.lookup_by_plate(db, officer=officer, plate=plate)


@router.post("/entries", response_model=TruckEntryOut,
             status_code=status.HTTP_201_CREATED)
def sign_in(
    body: TruckSignInRequest,
    response: Response,
    officer: CurrentOfficer = Depends(require_entry_writer),
    db: Session = Depends(get_db),
) -> TruckEntryOut:
    entry, created = truck_service.sign_in(db, officer=officer, data=body)
    if not created:
        response.status_code = status.HTTP_200_OK  # idempotent replay
    return entry


@router.post("/entries/{entry_id}/enter", response_model=TruckEntryOut)
def enter(
    entry_id: uuid.UUID,
    body: TruckEnterRequest,
    officer: CurrentOfficer = Depends(require_entry_writer),
    db: Session = Depends(get_db),
) -> TruckEntryOut:
    """Let a queued truck in; the driver signs."""
    return truck_service.enter(db, officer=officer, entry_id=entry_id, data=body)


@router.post("/entries/{entry_id}/leave-queue", response_model=TruckEntryOut)
def leave_queue(
    entry_id: uuid.UUID,
    body: TruckLeaveQueueRequest,
    officer: CurrentOfficer = Depends(require_entry_writer),
    db: Session = Depends(get_db),
) -> TruckEntryOut:
    """A queued truck gave up and left. A reason is required."""
    return truck_service.leave_queue(db, officer=officer, entry_id=entry_id, data=body)


@router.post("/entries/{entry_id}/sign-out", response_model=TruckEntryOut)
def sign_out(
    entry_id: uuid.UUID,
    body: TruckSignOutRequest,
    officer: CurrentOfficer = Depends(require_entry_writer),
    db: Session = Depends(get_db),
) -> TruckEntryOut:
    return truck_service.sign_out(db, officer=officer, entry_id=entry_id, data=body)


# ---- reads: everyone, scoped by get_facility_scope ----

@router.get("/entries", response_model=list[TruckEntryOut])
def list_entries(
    plate: Optional[str] = Query(None, max_length=40),
    filters: EntryFilters = Depends(),
    scope: Optional[uuid.UUID] = Depends(get_facility_scope),
    db: Session = Depends(get_db),
) -> list[TruckEntryOut]:
    rows = q.list_entries(db, scope=scope, plate=plate, **filters.as_kwargs())
    return [TruckEntryOut.from_row(r) for r in rows]


@router.get("/entries/{entry_id}/signature")
def get_signature(
    entry_id: uuid.UUID,
    side: SignatureSide = "in",
    scope: Optional[uuid.UUID] = Depends(get_facility_scope),
    db: Session = Depends(get_db),
) -> Response:
    """The PNG signed on the way in (`?side=in`, default) or out (`?side=out`)."""
    return signature_response(q.get_signature(db, entry_id, scope, side))
