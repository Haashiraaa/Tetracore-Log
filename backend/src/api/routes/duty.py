# backend/src/api/routes/duty.py

"""Security officers' duty log. Writes: an account that belongs to a facility logs ITSELF.
Reads: everyone, scoped by get_facility_scope."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from backend.src.api import duty_service
from backend.src.api.deps import get_facility_scope, require_entry_writer
from backend.src.api.routes._entries import EntryFilters, SignatureSide, signature_response
from backend.src.api.schemas import (
    CurrentOfficer,
    DutyChangeGateRequest,
    DutyEntryOut,
    DutyOffRequest,
    DutyOnRequest,
    DutyStatusOut,
)
from backend.src.db.queries import duty as q
from backend.src.db.session import get_db

router = APIRouter(prefix="/duty", tags=["duty"])


# ---- writes: an officer logs themselves ----

@router.get("", response_model=DutyStatusOut)
def my_status(
    officer: CurrentOfficer = Depends(require_entry_writer),
    db: Session = Depends(get_db),
) -> DutyStatusOut:
    """The gates of my facility and where I am on duty (`current` is null when off duty)."""
    return duty_service.status(db, officer=officer)


@router.post("/on", response_model=DutyEntryOut, status_code=status.HTTP_201_CREATED)
def go_on(
    body: DutyOnRequest,
    response: Response,
    officer: CurrentOfficer = Depends(require_entry_writer),
    db: Session = Depends(get_db),
) -> DutyEntryOut:
    entry, created = duty_service.go_on(db, officer=officer, data=body)
    if not created:
        response.status_code = status.HTTP_200_OK  # idempotent replay
    return entry


@router.post("/change-gate", response_model=DutyEntryOut, status_code=status.HTTP_201_CREATED)
def change_gate(
    body: DutyChangeGateRequest,
    response: Response,
    officer: CurrentOfficer = Depends(require_entry_writer),
    db: Session = Depends(get_db),
) -> DutyEntryOut:
    entry, created = duty_service.change_gate(db, officer=officer, data=body)
    if not created:
        response.status_code = status.HTTP_200_OK
    return entry


@router.post("/off", response_model=DutyStatusOut)
def go_off(
    body: DutyOffRequest,
    officer: CurrentOfficer = Depends(require_entry_writer),
    db: Session = Depends(get_db),
) -> DutyStatusOut:
    return duty_service.go_off(db, officer=officer, data=body)


# ---- reads: everyone, scoped ----

@router.get("/now", response_model=list[DutyEntryOut])
def on_duty_now(
    scope: Optional[uuid.UUID] = Depends(get_facility_scope),
    db: Session = Depends(get_db),
) -> list[DutyEntryOut]:
    """Who is on duty right now, and at which gate."""
    return duty_service.on_duty_now(db, scope=scope)


@router.get("/entries", response_model=list[DutyEntryOut])
def list_entries(
    filters: EntryFilters = Depends(),
    scope: Optional[uuid.UUID] = Depends(get_facility_scope),
    db: Session = Depends(get_db),
) -> list[DutyEntryOut]:
    rows = q.list_entries(db, scope=scope, **filters.as_kwargs())
    return [DutyEntryOut.from_row(r) for r in rows]


@router.get("/entries/{entry_id}/signature")
def get_signature(
    entry_id: uuid.UUID,
    side: SignatureSide = "in",
    scope: Optional[uuid.UUID] = Depends(get_facility_scope),
    db: Session = Depends(get_db),
) -> Response:
    """The PNG signed on going on duty (`?side=in`, default) or off (`?side=out`)."""
    return signature_response(q.get_signature(db, entry_id, scope, side))
