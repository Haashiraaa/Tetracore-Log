# backend/src/api/routes/waybill.py

"""Waybill log: sign in, sign out, list, signatures."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from backend.src.api import waybill_service
from backend.src.api.deps import get_facility_scope, require_entry_writer
from backend.src.api.routes._entries import (
    EntryFilters,
    PhoneQuery,
    PhoneSearchQuery,
    SignatureSide,
    signature_response,
)
from backend.src.api.schemas import (
    CurrentOfficer,
    PersonSignOutRequest,
    WaybillEntryOut,
    WaybillLookupOut,
    WaybillSignInRequest,
)
from backend.src.db.queries import waybill as q
from backend.src.db.session import get_db

router = APIRouter(prefix="/waybill", tags=["waybill"])


@router.get("/lookup", response_model=Optional[WaybillLookupOut])
def lookup(
    phone: PhoneQuery,
    officer: CurrentOfficer = Depends(require_entry_writer),
    db: Session = Depends(get_db),
) -> Optional[WaybillLookupOut]:
    """null = new here. Otherwise what was written last time, to CONFIRM, plus
    open_entry_id if they are inside now."""
    return waybill_service.lookup(db, officer=officer, phone=phone)


@router.get("/search", response_model=list[WaybillLookupOut])
def search(
    typed: PhoneSearchQuery,
    officer: CurrentOfficer = Depends(require_entry_writer),
    db: Session = Depends(get_db),
) -> list[WaybillLookupOut]:
    """Matches for the digits typed so far (3 or more), best match first. [] = no one yet."""
    return waybill_service.search(db, officer=officer, digits=typed)


@router.post("/entries", response_model=WaybillEntryOut, status_code=status.HTTP_201_CREATED)
def sign_in(
    body: WaybillSignInRequest,
    response: Response,
    officer: CurrentOfficer = Depends(require_entry_writer),
    db: Session = Depends(get_db),
) -> WaybillEntryOut:
    entry, created = waybill_service.sign_in(db, officer=officer, data=body)
    if not created:
        response.status_code = status.HTTP_200_OK  # idempotent replay
    return entry


@router.post("/entries/{entry_id}/sign-out", response_model=WaybillEntryOut)
def sign_out(
    entry_id: uuid.UUID,
    body: PersonSignOutRequest,
    officer: CurrentOfficer = Depends(require_entry_writer),
    db: Session = Depends(get_db),
) -> WaybillEntryOut:
    return waybill_service.sign_out(db, officer=officer, entry_id=entry_id, data=body)


@router.get("/entries", response_model=list[WaybillEntryOut])
def list_entries(
    filters: EntryFilters = Depends(),
    scope: Optional[uuid.UUID] = Depends(get_facility_scope),
    db: Session = Depends(get_db),
) -> list[WaybillEntryOut]:
    rows = q.list_entries(db, scope=scope, **filters.as_kwargs())
    return [WaybillEntryOut.from_row(r) for r in rows]


@router.get("/entries/{entry_id}/signature")
def get_signature(
    entry_id: uuid.UUID,
    side: SignatureSide = "in",
    scope: Optional[uuid.UUID] = Depends(get_facility_scope),
    db: Session = Depends(get_db),
) -> Response:
    """The PNG signed on the way in (`?side=in`, default) or out (`?side=out`)."""
    return signature_response(q.get_signature(db, entry_id, scope, side))
